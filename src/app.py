import os
import logging
import time
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.cloud import secretmanager
from google.api_core import exceptions as google_exceptions
import openai
import google.auth
from google.auth.exceptions import DefaultCredentialsError
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask with correct template and static folders
app = Flask(__name__,
            template_folder='templates',
            static_folder='static',
            static_url_path='/static')

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

logger.info(f"Starting application with PROJECT_ID: {PROJECT_ID}")

# Initialize Secret Manager client
try:
    secret_client = secretmanager.SecretManagerServiceClient()
    logger.info("Secret Manager client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Secret Manager client: {str(e)}", exc_info=True)
    secret_client = None

# Attempt to load default credentials
try:
    credentials, project = google.auth.default()
    logger.info(f"Default credentials loaded. Project: {project}")
except DefaultCredentialsError as e:
    logger.error(f"Failed to load default credentials: {str(e)}")

def access_secret_version(secret_id, version_id="latest"):
    logger.debug(f"Attempting to access secret: {secret_id}")
    if not secret_client or not PROJECT_ID:
        logger.warning(f"Secret Manager client or PROJECT_ID not available. secret_client: {secret_client}, PROJECT_ID: {PROJECT_ID}")
        env_var = os.environ.get(secret_id.upper().replace('-', '_'))
        logger.debug(f"Falling back to environment variable {secret_id.upper().replace('-', '_')}: {'Set' if env_var else 'Not set'}")
        return env_var.strip() if env_var else None
    
    try:
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
        logger.debug(f"Requesting secret from: {name}")
        response = secret_client.access_secret_version(name=name)
        secret_value = response.payload.data.decode("UTF-8").strip()
        logger.info(f"Successfully accessed secret: {secret_id}")
        logger.debug(f"Secret value (first 5 chars): {secret_value[:5]}...")
        return secret_value
    except google_exceptions.InvalidArgument as e:
        logger.error(f"Invalid argument when accessing secret {secret_id}: {str(e)}")
    except google_exceptions.NotFound as e:
        logger.error(f"Secret {secret_id} not found: {str(e)}")
    except google_exceptions.PermissionDenied as e:
        logger.error(f"Permission denied when accessing secret {secret_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error accessing secret {secret_id}: {str(e)}", exc_info=True)
    
    env_var = os.environ.get(secret_id.upper().replace('-', '_'))
    logger.debug(f"Falling back to environment variable {secret_id.upper().replace('-', '_')}: {'Set' if env_var else 'Not set'}")
    return env_var.strip() if env_var else None

# Fetch secrets
OPENAI_API_KEY = access_secret_version("openai-api-key")
ASSISTANT_ID = access_secret_version("openai-assistant-id")

# Set up OpenAI
openai.api_key = OPENAI_API_KEY
logger.info(f"OpenAI API key configured: {'Yes' if openai.api_key else 'No'}")

# Routes
@app.route('/')
def index():
    logger.debug("Rendering index page")
    return render_template('index.html', client_id=CLIENT_ID)

@app.route('/health')
def health_check():
    logger.debug("Health check endpoint called")
    return jsonify({"status": "healthy"}), 200

@app.route('/submit', methods=['POST'])
def submit():
    logger.debug("Received submit request")
    if 'credential' not in request.form:
        logger.error("No credential provided")
        return jsonify({"error": "No credential provided"}), 400

    try:
        logger.debug(f"Verifying token with Client ID: {CLIENT_ID}")
        idinfo = id_token.verify_oauth2_token(request.form['credential'], google_requests.Request(), CLIENT_ID)
        
        user_id = idinfo['sub']
        email = idinfo['email']
        logger.debug(f"Successfully authenticated user: {email}")
        
        session['user_email'] = email
        return redirect(url_for('authorized'))
    
    except ValueError as e:
        logger.error(f"Token verification failed: {str(e)}")
        return jsonify({"error": "Invalid token"}), 400

@app.route('/authorized')
def authorized():
    logger.debug("Accessing authorized page")
    if 'user_email' not in session:
        logger.warning("User not authenticated, redirecting to index")
        return redirect(url_for('index'))
    return render_template('authorized.html', email=session['user_email'])

@app.route('/process_form', methods=['POST'])
def process_form():
    logger.debug("Process form function called")
    try:
        data = request.get_json()
        form_type = data.get('formType')
        base_prompt = data.get('prompt', '')

        # Create form-specific prompt structure
        message_content = f"{base_prompt}\n\n"
        
        # Add form-specific formatting based on form type
        if form_type == 'medical':
            message_content += f"""
            Patient Medical History Analysis Request:
            Patient Name: {data.get('name')}
            Age: {data.get('age')}
            Medical History: {data.get('history')}
            
            Please provide:
            1. Analysis of medical history
            2. Potential dental treatment considerations
            3. Recommended precautions
            4. Additional medical clearance needs
            """
        elif form_type == 'dental':
            message_content += f"""
            Dental Examination Analysis Request:
            Tooth Condition: {data.get('toothCondition')}
            X-Ray Findings: {data.get('xrayFindings')}
            Current Symptoms: {data.get('symptoms')}
            
            Please provide:
            1. Comprehensive dental analysis
            2. Potential diagnosis
            3. Treatment recommendations
            4. Additional examination needs
            """
        elif form_type == 'medication':
            message_content += f"""
            Medication Review Request:
            Current Medications: {data.get('currentMeds')}
            Allergies: {data.get('allergies')}
            Past Adverse Reactions: {data.get('reactions')}
            
            Please provide:
            1. Medication interaction analysis
            2. Dental treatment considerations
            3. Recommended precautions
            4. Alternative medication suggestions if needed
            """
        elif form_type == 'treatment':
            message_content += f"""
            Treatment Plan Analysis Request:
            Current Diagnosis: {data.get('diagnosis')}
            Proposed Treatment: {data.get('proposed')}
            Alternative Options: {data.get('alternatives')}
            
            Please provide:
            1. Treatment plan analysis
            2. Risk assessment
            3. Success rate estimation
            4. Recovery timeline
            """

        logger.debug("Prepared message for OpenAI")
        
        # OpenAI interaction
        try:
            if not openai.api_key:
                logger.error("OpenAI API key is not set")
                return jsonify({"error": "OpenAI API key is not configured"}), 500

            thread = openai.beta.threads.create()
            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message_content
            )

            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Wait for completion
            timeout = time.time() + 60
            while run.status != 'completed':
                if time.time() > timeout:
                    logger.error("Assistant run timed out")
                    return jsonify({"error": "Assistant run timed out"}), 504
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_message = next((msg for msg in reversed(messages.data) if msg.role == 'assistant'), None)
            
            if assistant_message is None:
                return jsonify({"error": "No response from assistant"}), 500
            
            assessment = assistant_message.content[0].text.value
            return jsonify({"result": assessment})

        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({"error": f"Error communicating with OpenAI API: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error processing form: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the form"}), 500

@app.route('/download_report/<filename>')
def download_report(filename):
    logger.debug(f"Download report requested for: {filename}")
    try:
        return send_from_directory(app.static_folder, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({"error": "File not found"}), 404

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 error: {error}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)