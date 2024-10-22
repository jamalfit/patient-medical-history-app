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
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'patient-medical-history-app')  # Added default project ID

logger.info(f"Starting application with PROJECT_ID: {PROJECT_ID}")

# Initialize Secret Manager client with retry logic
def initialize_secret_client():
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            client = secretmanager.SecretManagerServiceClient()
            logger.info("Secret Manager client initialized successfully")
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed to initialize Secret Manager client: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to initialize Secret Manager client after {max_retries} attempts: {str(e)}", exc_info=True)
                return None

secret_client = initialize_secret_client()

# Attempt to load default credentials
try:
    credentials, project = google.auth.default()
    logger.info(f"Default credentials loaded. Project: {project}")
except DefaultCredentialsError as e:
    logger.error(f"Failed to load default credentials: {str(e)}")

def access_secret_version(secret_id, version_id="latest"):
    """Enhanced secret access with better fallback mechanisms"""
    logger.debug(f"Attempting to access secret: {secret_id}")
    
    # First try environment variables
    env_var = os.environ.get(secret_id.upper().replace('-', '_'))
    if env_var:
        logger.debug(f"Found secret in environment variables: {secret_id}")
        return env_var.strip()
    
    # Then try Secret Manager with multiple project ID fallbacks
    project_ids = [
        PROJECT_ID,
        os.environ.get('GOOGLE_CLOUD_PROJECT'),
        'patient-medical-history-app'
    ]
    
    for project_id in project_ids:
        if not project_id or not secret_client:
            continue
            
        try:
            name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
            logger.debug(f"Requesting secret from: {name}")
            response = secret_client.access_secret_version(name=name)
            secret_value = response.payload.data.decode("UTF-8").strip()
            logger.info(f"Successfully accessed secret: {secret_id}")
            logger.debug(f"Secret value (first 5 chars): {secret_value[:5]}...")
            return secret_value
            
        except google_exceptions.InvalidArgument as e:
            logger.warning(f"Invalid argument when accessing secret {secret_id} in project {project_id}: {str(e)}")
        except google_exceptions.NotFound as e:
            logger.warning(f"Secret {secret_id} not found in project {project_id}: {str(e)}")
        except google_exceptions.PermissionDenied as e:
            logger.warning(f"Permission denied when accessing secret {secret_id} in project {project_id}: {str(e)}")
        except Exception as e:
            logger.warning(f"Unexpected error accessing secret {secret_id} in project {project_id}: {str(e)}")
    
    # Final fallback to environment variables
    env_var = os.environ.get(secret_id.upper().replace('-', '_'))
    if env_var:
        logger.debug(f"Falling back to environment variable {secret_id.upper().replace('-', '_')}: Set")
        return env_var.strip()
    
    logger.error(f"Failed to access secret {secret_id} from all sources")
    return None

# Fetch secrets with validation
def initialize_secrets():
    """Initialize and validate required secrets"""
    openai_api_key = access_secret_version("openai-api-key")
    assistant_id = access_secret_version("openai-assistant-id")
    
    if not openai_api_key:
        logger.error("OpenAI API key not found in any source")
        raise RuntimeError("OpenAI API key is required but not found")
        
    if not assistant_id:
        logger.error("OpenAI Assistant ID not found in any source")
        raise RuntimeError("OpenAI Assistant ID is required but not found")
        
    return openai_api_key, assistant_id

try:
    OPENAI_API_KEY, ASSISTANT_ID = initialize_secrets()
    openai.api_key = OPENAI_API_KEY
    logger.info("OpenAI configuration completed successfully")
except Exception as e:
    logger.error(f"Failed to initialize secrets: {str(e)}")
    OPENAI_API_KEY = None
    ASSISTANT_ID = None

# [Rest of your existing code remains the same, starting from the routes...]