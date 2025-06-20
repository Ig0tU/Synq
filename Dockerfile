# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables for Python and Numba
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Remove NUMBA_DISABLE_JIT=1 here. We want Numba to work if versions are compatible.
    # NUMBA_DISABLE_JIT=1 \
    NUMBA_CACHE_DIR=/tmp/numba_cache

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install build dependencies
# Keep these as they are essential for various Python packages including those with C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        llvm \
        clang \
        build-essential \
        libedit-dev \
        libffi-dev \
        python3-dev \
        libgl1-mesa-glx \
        libsm6 \
        libxrender1 \
        libglib2.0-0 \
        ffmpeg \
        # Ensure you have these for audio processing if they are not covered by librosa's dependencies
        libsndfile1 \
        libsndfile1-dev \
        && rm -rf /var/lib/apt/lists/*

# Set LLVM_CONFIG before building llvmlite (if needed) - crucial for older numba/llvmlite
# For numba 0.48.0, often llvm-config-8 or llvm-config-9 is needed.
# Let's try llvm-config-9, as Python 3.9 is relatively new for 0.48.0, but it often works.
# If this fails, try installing llvm-9-dev and setting LLVM_CONFIG=/usr/bin/llvm-config-9
ENV LLVM_CONFIG=/usr/bin/llvm-config

# Explicitly install compatible versions of core audio/Numba stack
# Order matters: numpy -> llvmlite -> numba -> resampy -> librosa
RUN pip install --no-cache-dir \
    numpy==1.22.4 \
    llvmlite==0.35.0 \
    numba==0.48.0 \
    resampy==0.2.2 \
    librosa==0.8.1 # librosa 0.8.1 is often good with resampy 0.2.2

# Install other Python dependencies from requirements.txt
# This will pick up all other packages, assuming they don't conflict with the explicitly installed ones.
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