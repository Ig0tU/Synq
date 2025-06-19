# Use Python 3.9 base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Set working directory
WORKDIR /app

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt
COPY requirements.txt .

# Upgrade pip to avoid version issues and install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port for Hugging Face
EXPOSE 7860

# Start the Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
