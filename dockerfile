# Use Python 3.9 base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the Python scripts to the container
COPY . .

# Default command to override with docker-compose
CMD ["python", "tracker.py"]
