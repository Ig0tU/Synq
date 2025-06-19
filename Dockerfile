FROM python:3.9-slim

# Environment config
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    LLVM_CONFIG=/usr/lib/llvm-10/bin/llvm-config

# Working directory
WORKDIR /app

# Install system dependencies including LLVM 10
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    build-essential \
    llvm-10 \
    llvm-10-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install numpy early (needed for numba)
RUN pip install --upgrade pip
RUN pip install numpy==1.21.6

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port
EXPOSE 7860

# Run app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
