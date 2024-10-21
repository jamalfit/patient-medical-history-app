import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.cloud import secretmanager
import openai
from ai_prompt import get_medical_report_prompt

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

# Initialize Secret Manager client
try:
    secret_client = secretmanager.SecretManagerServiceClient()
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

logger.info(f"Application initialized with CLIENT_ID: {CLIENT_ID}, PROJECT_ID: {PROJECT_ID}")

def calculate_bmi(height_inches, weight_pounds):
    height_meters = height_inches * 0.0254
    weight_kg = weight_pounds * 0.453592
    bmi = weight_kg / (height_meters ** 2)
    return round(bmi, 2)

def generate_medical_report(patient_data):
    logger.debug("Generating medical report using OpenAI Assistant")
    if not OPENAI_API_KEY or not ASSISTANT_ID:
        logger.error("OpenAI credentials not available. Cannot generate report.")
        return "Error: OpenAI credentials not configured correctly."
    
    try:
        prompt = get_medical_report_prompt(patient_data)
        logger.debug(f"Prompt sent to OpenAI: {prompt}")
        
        # Create a thread
        thread = openai.beta.threads.create()

        # Add a message to the thread
        message = openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Wait for the run to complete
        while run.status != 'completed':
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        # Retrieve the messages
        messages = openai.beta.threads.messages.list(thread_id=thread.id)

        # Get the last message (the assistant's response)
        assistant_message = next(msg for msg in messages if msg.role == 'assistant')
        report = assistant_message.content[0].text.value

        logger.debug(f"Processed text from OpenAI Assistant: {report}")
        return report
    except Exception as e:
        logger.error(f"Error generating medical report: {str(e)}")
        return f"Error generating report: {str(e)}"

@app.route('/')
def index():
    logger.debug("Rendering index page")
    return render_template('index.html', client_id=CLIENT_ID)

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
    logger.debug("Processing patient form")
    try:
        name = request.form.get('name')
        age = int(request.form.get('age'))
        height = float(request.form.get('height'))
        weight = float(request.form.get('weight'))
        current_meds = request.form.get('current_meds')
        allergies = request.form.get('allergies')
        medical_conditions = request.form.get('medical_conditions')
        medical_history = request.form.get('medical_history')
        email = session.get('user_email')
        
        bmi = calculate_bmi(height, weight)
        
        patient_data = {
            "age": age,
            "bmi": bmi,
            "current_meds": current_meds,
            "allergies": allergies,
            "medical_conditions": medical_conditions,
            "medical_history": medical_history
        }
        
        ai_response = generate_medical_report(patient_data)
        logger.debug(f"AI Response: {ai_response}")
        
        # Parse the AI response
        sections = {
            "ASA Physical Status Classification": "",
            "Medication Analysis": "",
            "Medical Evaluation": "",
            "Recommendations": "",
            "Risk Assessment": "",
            "Additional Notes": ""
        }

        if "Error" in ai_response:
            for section in sections:
                sections[section] = "Error generating this section. Please try again."
        else:
            current_section = None
            for line in ai_response.split('\n'):
                if any(section in line for section in sections.keys()):
                    current_section = next(section for section in sections.keys() if section in line)
                elif current_section:
                    sections[current_section] += line + '\n'

        for section, content in sections.items():
            logger.debug(f"{section}: {content[:100]}...")  # Log first 100 chars of each section

        logger.debug("Form processed successfully, rendering result")
        return render_template('result.html', 
                               name=name, 
                               age=age, 
                               height=height, 
                               weight=weight, 
                               bmi=bmi,
                               current_meds=current_meds,
                               allergies=allergies,
                               medical_conditions=medical_conditions,
                               medical_history=medical_history,
                               email=email,
                               **sections)
    except Exception as e:
        logger.error(f"Error processing form: {str(e)}")
        return jsonify({"error": "An error occurred while processing the form"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))