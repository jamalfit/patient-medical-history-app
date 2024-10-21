import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests
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
secret_client = secretmanager.SecretManagerServiceClient()

def access_secret_version(secret_id, version_id="latest"):
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Fetch secrets
OPENAI_API_KEY = access_secret_version("openai-api-key")
ASSISTANT_ID = access_secret_version("openai-assistant-id")

# Set up OpenAI
openai.api_key = OPENAI_API_KEY

logger.debug(f"Starting application with CLIENT_ID: {CLIENT_ID}")

def calculate_bmi(height_inches, weight_pounds):
    height_meters = height_inches * 0.0254
    weight_kg = weight_pounds * 0.453592
    bmi = weight_kg / (height_meters ** 2)
    return round(bmi, 2)

def generate_medical_report(patient_data):
    logger.debug("Generating medical report using OpenAI Assistant")
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

# ... (rest of the Flask routes remain the same)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))