import os
from flask import Flask, render_template, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
print(f"Startup: Using Client ID: {CLIENT_ID}")  # Add this line for logging

@app.route('/')
def index():
    return render_template('index.html', client_id=CLIENT_ID)

@app.route('/submit', methods=['POST'])
def submit():
    print("Received submit request")  # Add this line for logging
    if 'credential' not in request.form:
        print("No credential provided")  # Add this line for logging
        return jsonify({"error": "No credential provided"}), 400

    try:
        print(f"Verifying token with Client ID: {CLIENT_ID}")  # Add this line for logging
        idinfo = id_token.verify_oauth2_token(
            request.form['credential'], requests.Request(), CLIENT_ID)

        user_id = idinfo['sub']
        email = idinfo['email']
        print(f"Successfully authenticated user: {email}")  # Add this line for logging

        return jsonify({"message": "Successfully authenticated", "email": email})

    except ValueError as e:
        print(f"Token verification failed: {str(e)}")  # Add this line for logging
        return jsonify({"error": "Invalid token"}), 400

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
