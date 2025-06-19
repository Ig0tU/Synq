FROM python:3.9-slim

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    llvm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pre-install numpy to resolve numba setup dependency
RUN pip install --upgrade pip
RUN pip install numpy==1.21.6

# Copy requirements and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Expose Hugging Face Gradio/Flask port
EXPOSE 7860

# Launch app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
