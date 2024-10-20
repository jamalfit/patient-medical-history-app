import os
from flask import Flask, render_template, request, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests
from google.cloud import storage, secretmanager, aiplatform

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Get the Google Client ID from the environment variable
CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

@app.route('/')
def index():
    return render_template('index.html', client_id=CLIENT_ID)

@app.route('/submit', methods=['POST'])
def submit():
    if 'credential' not in request.form:
        return "No credential provided", 400

    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(request.form['credential'], requests.Request(), CLIENT_ID)
        
        # Get user info from the ID token
        user_id = idinfo['sub']
        email = idinfo['email']
        
        # Process form data
        name = request.form['name']
        age = request.form['age']
        medical_history = request.form['medical_history']
        
        # Here you would typically process the data, maybe use Vertex AI, etc.
        # For this example, we'll just pass the data to the result template
        
        return render_template('result.html', name=name, age=age, medical_history=medical_history, email=email)
    
    except ValueError:
        # Invalid token
        return "Invalid token", 400

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))