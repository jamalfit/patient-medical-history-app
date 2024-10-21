import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
print(f"Startup: Using Client ID: {CLIENT_ID}")

@app.route('/')
def index():
    return render_template('index.html', client_id=CLIENT_ID)

@app.route('/submit', methods=['POST'])
def submit():
    print("Received submit request")
    if 'credential' not in request.form:
        print("No credential provided")
        return jsonify({"error": "No credential provided"}), 400

    try:
        print(f"Verifying token with Client ID: {CLIENT_ID}")
        idinfo = id_token.verify_oauth2_token(request.form['credential'], requests.Request(), CLIENT_ID)
        
        user_id = idinfo['sub']
        email = idinfo['email']
        print(f"Successfully authenticated user: {email}")
        
        # Store user information in session
        session['user_email'] = email
        
        # Redirect to the patient form page
        return redirect(url_for('patient_form'))
    
    except ValueError as e:
        print(f"Token verification failed: {str(e)}")
        return jsonify({"error": "Invalid token"}), 400

@app.route('/patient_form')
def patient_form():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('patient_form.html', email=session['user_email'])

@app.route('/process_form', methods=['POST'])
def process_form():
    name = request.form.get('name')
    age = request.form.get('age')
    medical_history = request.form.get('medical_history')
    email = session.get('user_email')
    
    # Here you would typically process the form data, maybe store it in a database
    # For now, we'll just render a result page
    return render_template('result.html', name=name, age=age, medical_history=medical_history, email=email)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))