# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the src directory
COPY src/ src/

# Add the current directory to PYTHONPATH
ENV PYTHONPATH=/app/src
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PORT=8080

# Expose port
EXPOSE 8080

# Change working directory to src
WORKDIR /app/src

# Update the Gunicorn command to use the correct module path
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app --log-level debug