# Use an official Python runtime as a parent image (Debian 12 Bookworm)
FROM python:3.9-slim

# Disable Python bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Ensure NumPy <2 so all C extensions load correctly
    NUMPY_EXPLICIT_VERSION=1.23.5

# Working directory
WORKDIR /app

# Install build dependencies, audio/video libs, and LLVM 14 for llvmlite
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libedit-dev \
        libffi-dev \
        python3-dev \
        libgl1-mesa-glx libsm6 libxrender1 libglib2.0-0 \
        ffmpeg \
        libsndfile1 libsndfile1-dev \
        clang-14 llvm-14-dev llvm-14-runtime \
    && rm -rf /var/lib/apt/lists/*

# Point llvmlite at the correct llvm-config
ENV LLVM_CONFIG=/usr/bin/llvm-config-14

# Remove any preinstalled NumPy, then install a NumPy 1.x release
RUN pip uninstall -y numpy || true && \
    pip install --no-cache-dir numpy==${NUMPY_EXPLICIT_VERSION}

# Install the trio that need to compile against NumPy 1.x
RUN pip install --no-cache-dir \
      llvmlite==0.38.0 \
      numba==0.55.2 \
      resampy==0.3.1 \
      librosa==0.9.2

# Copy your application requirements (must NOT re‑pin NumPy)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create and permissively chmod required directories
RUN mkdir -p cache uploads results checkpoints temp && \
    chmod -R 777 cache uploads results checkpoints temp

# Ensure the entire app directory is writable
RUN chmod -R 777 /app

# Expose the inference port
EXPOSE 7860

# Environment variables for Flask
ENV FLASK_APP=app.py \
    FLASK_ENV=production

# Launch with Gunicorn (defaults: 1 worker, sync, 30s timeout)
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
