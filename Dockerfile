# Use a small, official Python base image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (for effective layer caching)
COPY requirements.txt /app/

# Install the Python dependencies
# The --no-cache-dir flag keeps the image size small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app/

# Expose the port (FastAPI/Uvicorn default is often 8000)
EXPOSE 8000

# Define the command to run your application when the container starts
# Replace 'main.py' with your actual entry point script
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]