import os
from flask import Flask, render_template, request, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests
from google.cloud import aiplatform
from vertexai.language_models import TextGenerationModel

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
LOCATION = 'us-central1'  # Replace with your preferred location

aiplatform.init(project=PROJECT_ID, location=LOCATION)

def calculate_bmi(height_inches, weight_pounds):
    height_meters = height_inches * 0.0254
    weight_kg = weight_pounds * 0.453592
    bmi = weight_kg / (height_meters ** 2)
    return round(bmi, 2)

def generate_medical_report(patient_data):
    model = TextGenerationModel.from_pretrained("text-bison@001")
    prompt = f"""
    Based on the following patient information, provide an ASA Physical Status Classification and a brief report on the patient's medications. Include any potential interactions or concerns.

    Patient Information:
    Age: {patient_data['age']}
    BMI: {patient_data['bmi']}
    Current Medications: {patient_data['current_meds']}
    Allergies: {patient_data['allergies']}
    Medical Conditions: {patient_data['medical_conditions']}
    Medical History: {patient_data['medical_history']}

    Please format your response as follows:
    ASA Status: [Your assessment]
    
    Medication Report:
    [Your detailed report on medications, potential interactions, and concerns]
    """

    response = model.predict(prompt, max_output_tokens=1024, temperature=0.2)
    return response.text

@app.route('/')
def index():
    return render_template('index.html', client_id=CLIENT_ID)

@app.route('/submit', methods=['POST'])
def submit():
    # ... (keep the existing authentication code)

@app.route('/patient_form')
def patient_form():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('patient_form.html', email=session['user_email'])

@app.route('/process_form', methods=['POST'])
def process_form():
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
    
    # Split the AI response into ASA Status and Medication Report
    asa_status = "Unknown"
    medication_report = ai_response
    if "ASA Status:" in ai_response:
        parts = ai_response.split("Medication Report:", 1)
        asa_status = parts[0].split("ASA Status:", 1)[1].strip()
        medication_report = parts[1].strip() if len(parts) > 1 else ""
    
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
                           medication_report=medication_report)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))