FROM python:3.9-slim-bullseye

# Environment
ENV PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install numpy before llvmlite/numba
RUN pip install --upgrade pip
RUN pip install numpy==1.21.6

# Install Gunicorn and app dependencies
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p cache uploads results checkpoints temp \
    && chmod -R 777 cache uploads results checkpoints temp

# Copy application code
COPY . .

EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]