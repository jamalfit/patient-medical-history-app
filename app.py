import os
import logging
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.cloud import secretmanager
import openai

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

logger.info(f"Starting application with PROJECT_ID: {PROJECT_ID}")

# Initialize Secret Manager client
try:
    secret_client = secretmanager.SecretManagerServiceClient()
    logger.info("Secret Manager client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Secret Manager client: {str(e)}")
    secret_client = None

def access_secret_version(secret_id, version_id="latest"):
    if not secret_client or not PROJECT_ID:
        logger.warning(f"Secret Manager not available. Falling back to environment variable for {secret_id}")
        return os.environ.get(secret_id.upper().replace('-', '_'))
    
    try:
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
        response = secret_client.access_secret_version(request={"name": name})
        logger.info(f"Successfully accessed secret: {secret_id}")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error accessing secret {secret_id}: {str(e)}")
        return os.environ.get(secret_id.upper().replace('-', '_'))

# Fetch secrets or use environment variables as fallback
OPENAI_API_KEY = access_secret_version("openai-api-key")
ASSISTANT_ID = access_secret_version("openai-assistant-id")

if not OPENAI_API_KEY:
    logger.error("OpenAI API key not available. The application may not function correctly.")
if not ASSISTANT_ID:
    logger.error("OpenAI Assistant ID not available. The application may not function correctly.")

# Set up OpenAI
openai.api_key = OPENAI_API_KEY

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
        return redirect(url_for('patient_form'))
    
    except ValueError as e:
        logger.error(f"Token verification failed: {str(e)}")
        return jsonify({"error": "Invalid token"}), 400

@app.route('/patient_form')
def patient_form():
    logger.debug("Rendering patient form")
    if 'user_email' not in session:
        logger.warning("User not authenticated, redirecting to index")
        return redirect(url_for('index'))
    return render_template('patient_form.html', email=session['user_email'])

@app.route('/process_form', methods=['POST'])
def process_form():
    logger.debug("Process form function called")
    try:
        # Log all form data (be careful with sensitive information in production)
        logger.debug(f"Received form data: {request.form}")

        # Extract form data
        name = request.form.get('name', '')
        age = request.form.get('age', '')
        height = request.form.get('height', '')
        weight = request.form.get('weight', '')
        medical_history = request.form.get('medical_history', '')
        current_medications = request.form.get('current_medications', '')
        allergies = request.form.get('allergies', '')

        logger.debug("Form data extracted successfully")

        # Prepare the message for the OpenAI assistant
        message_content = f"""
        Patient Information:
        Name: {name}
        Age: {age}
        Height: {height} inches
        Weight: {weight} lbs
        Medical History: {medical_history}
        Current Medications: {current_medications}
        Allergies: {allergies}

        Please provide a medical assessment including:
        1. BMI calculation and interpretation
        2. Analysis of current medications and potential interactions
        3. Assessment of overall health based on the provided information
        4. Recommendations for further tests or lifestyle changes if necessary
        """

        logger.debug("Message content prepared for OpenAI assistant")

        # OpenAI interaction
        try:
            logger.debug("Creating thread for OpenAI assistant")
            thread = openai.beta.threads.create()

            logger.debug("Adding message to thread")
            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message_content
            )

            logger.debug("Running assistant")
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Wait for the assistant to complete (with a timeout)
            logger.debug("Waiting for assistant to complete")
            timeout = time.time() + 60  # 60 second timeout
            while run.status != 'completed':
                if time.time() > timeout:
                    logger.error("Assistant run timed out")
                    return jsonify({"error": "Assistant run timed out"}), 504
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                logger.debug(f"Run status: {run.status}")

            logger.debug("Assistant run completed, retrieving messages")
            messages = openai.beta.threads.messages.list(thread_id=thread.id)

            # Get the last assistant message
            assistant_message = next((msg for msg in reversed(messages.data) if msg.role == 'assistant'), None)
            if assistant_message is None:
                logger.error("No assistant message found")
                return jsonify({"error": "No response from assistant"}), 500
            
            assessment = assistant_message.content[0].text.value

        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({"error": "Error communicating with OpenAI API"}), 500

        logger.debug("Rendering result template")
        return render_template('result.html', 
                               name=name, 
                               age=age, 
                               height=height, 
                               weight=weight,
                               medical_history=medical_history,
                               current_medications=current_medications,
                               allergies=allergies,
                               assessment=assessment)

    except Exception as e:
        logger.error(f"Error processing form: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while processing the form"}), 500

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