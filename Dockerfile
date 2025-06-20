# Use an official Python runtime as a parent image
# This base image is Debian 12 "Bookworm"
FROM python:3.9-slim

# Set environment variables for Python and Numba
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/tmp/numba_cache

# Set the working directory
WORKDIR /app

# Install build dependencies and LLVM components from Debian's default repos (Bookworm)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libedit-dev \
        libffi-dev \
        python3-dev \
        libgl1-mesa-glx \
        libsm6 \
        libxrender1 \
        libglib2.0-0 \
        ffmpeg \
        libsndfile1 \
        libsndfile1-dev \
        # Install LLVM 14, which is common in Debian Bookworm
        clang-14 \
        llvm-14-dev \
        llvm-14-runtime \
        && rm -rf /var/lib/apt/lists/*

# Set LLVM_CONFIG for clang-14 (needed by llvmlite)
ENV LLVM_CONFIG=/usr/bin/llvm-config-14

# --- CRITICAL CHANGE: Ensure correct NumPy version ---
# First, remove any pre-installed numpy that might conflict
RUN pip uninstall -y numpy || true

# Explicitly install the exact NumPy 1.x version
# This must come BEFORE numba and librosa to ensure they compile/install against it.
RUN pip install --no-cache-dir numpy==1.22.4

# Install llvmlite, numba, resampy, librosa which depend on numpy
RUN pip install --no-cache-dir \
    llvmlite==0.36.0 \
    numba==0.53.1 \
    resampy==0.3.1 \
    librosa==0.9.2

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install other Python dependencies from requirements.txt
# IT IS CRUCIAL that requirements.txt does NOT contain any numpy version that would conflict.
# If it does, you MUST remove or modify it.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/cache /app/uploads /app/results /app/checkpoints /app/temp \
 && chmod -R 777 /app/cache /app/uploads /app/results /app/checkpoints /app/temp

# Ensure full permissions for app directory
RUN chmod -R 777 /app

# Expose the app port
EXPOSE 7860

# Set Flask environment variables
ENV FLASK_APP=app.py \
    FLASK_ENV=production

# Start the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]