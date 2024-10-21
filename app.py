import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests
from google.cloud import aiplatform
from vertexai.language_models import TextGenerationModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
LOCATION = 'us-central1'  # Replace with your preferred location

logger.debug(f"Starting application with CLIENT_ID: {CLIENT_ID}, PROJECT_ID: {PROJECT_ID}")

try:
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    logger.debug("AI Platform initialized successfully")
except Exception as e:
    logger.error(f"Error initializing AI Platform: {str(e)}")

def calculate_bmi(height_inches, weight_pounds):
    height_meters = height_inches * 0.0254
    weight_kg = weight_pounds * 0.453592
    bmi = weight_kg / (height_meters ** 2)
    return round(bmi, 2)

def generate_medical_report(patient_data):
    logger.debug("Generating medical report")
    try:
        model = TextGenerationModel.from_pretrained("text-bison@001")
        prompt = f"""
        You are an AI medical assistant tasked with analyzing patient data and providing a comprehensive medical report. Your role is to:
        1. Determine the ASA Physical Status Classification based on the patient's information.
        2. Analyze the patient's current medications, considering potential interactions and side effects.
        3. Evaluate the patient's medical conditions and history in relation to their current status.
        4. Provide recommendations for further tests or consultations if necessary.
        5. Highlight any potential risks or areas of concern.

        Please use the following guidelines:
        - Be thorough and considerate in your analysis.
        - Use medical terminology where appropriate, but ensure the report is understandable to healthcare professionals.
        - If there's insufficient information to make a determination, state this clearly.
        - Be concise but comprehensive in your report.

        Patient Information:
        Age: {patient_data['age']}
        BMI: {patient_data['bmi']}
        Current Medications: {patient_data['current_meds']}
        Allergies: {patient_data['allergies']}
        Medical Conditions: {patient_data['medical_conditions']}
        Medical History: {patient_data['medical_history']}

        Please format your response as follows:

        ASA Status: [Your ASA Physical Status Classification]

        Medication Analysis:
        [Detailed analysis of current medications, potential interactions, and concerns]

        Medical Evaluation:
        [Evaluation of medical conditions and history]

        Recommendations:
        [Any recommended tests, consultations, or lifestyle changes]

        Risk Assessment:
        [Highlight of potential risks or areas of concern]

        Additional Notes:
        [Any other relevant information or observations]

        """

        response = model.predict(prompt, max_output_tokens=1024, temperature=0.2)
        logger.debug("Medical report generated successfully")
        return response.text
    except Exception as e:
        logger.error(f"Error generating medical report: {str(e)}")
        return "Error generating report"

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
        idinfo = id_token.verify_oauth2_token(request.form['credential'], requests.Request(), CLIENT_ID)
        
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
        
        # Parse the AI response
        asa_status = "Unknown"
        medication_analysis = ""
        medical_evaluation = ""
        recommendations = ""
        risk_assessment = ""
        additional_notes = ""

        sections = ai_response.split("\n\n")
        for section in sections:
            if section.startswith("ASA Status:"):
                asa_status = section.split(":", 1)[1].strip()
            elif section.startswith("Medication Analysis:"):
                medication_analysis = section.split(":", 1)[1].strip()
            elif section.startswith("Medical Evaluation:"):
                medical_evaluation = section.split(":", 1)[1].strip()
            elif section.startswith("Recommendations:"):
                recommendations = section.split(":", 1)[1].strip()
            elif section.startswith("Risk Assessment:"):
                risk_assessment = section.split(":", 1)[1].strip()
            elif section.startswith("Additional Notes:"):
                additional_notes = section.split(":", 1)[1].strip()
        
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
                               asa_status=asa_status,
                               medication_analysis=medication_analysis,
                               medical_evaluation=medical_evaluation,
                               recommendations=recommendations,
                               risk_assessment=risk_assessment,
                               additional_notes=additional_notes)
    except Exception as e:
        logger.error(f"Error processing form: {str(e)}")
        return jsonify({"error": "An error occurred while processing the form"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))