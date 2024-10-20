# Use the official Python image as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies with verbose output
RUN pip install --no-cache-dir -r requirements.txt -v

# Copy the rest of the application code into the container
COPY . .

# Print the contents of the current directory for debugging
RUN ls -la

# Print the contents of requirements.txt for debugging
RUN cat requirements.txt

# Specify the command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]