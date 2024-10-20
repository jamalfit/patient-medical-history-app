import os
from flask import Flask, render_template, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

@app.route('/')
def index():
    return render_template('index.html', client_id=CLIENT_ID)

@app.route('/submit', methods=['POST'])
def submit():
    if 'credential' not in request.form:
        return jsonify({"error": "No credential provided"}), 400

    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(request.form['credential'], requests.Request(), CLIENT_ID)
        
        # Get user info from the ID token
        user_id = idinfo['sub']
        email = idinfo['email']
        
        # Process form data (if any)
        # ...

        return jsonify({"message": "Successfully authenticated", "email": email})
    
    except ValueError:
        return jsonify({"error": "Invalid token"}), 400

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))