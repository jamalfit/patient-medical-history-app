# Use the official Python image as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set the environment variable for the port
ENV PORT 8080

# Specify the command to run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app