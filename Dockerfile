# Use an official Python runtime as a parent image
# This base image is Debian 12 "Bookworm"
FROM python:3.9-slim

# Set environment variables for Python and Numba
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/tmp/numba_cache

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

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

# Explicitly install NumPy 1.x first and then compatible versions of core audio/Numba stack
# Use --force-reinstall to ensure it's not a cached version that's causing issues.
RUN pip install --no-cache-dir --force-reinstall "numpy<2" \
    && pip install --no-cache-dir \
    llvmlite==0.36.0 \
    numba==0.53.1 \
    resampy==0.3.1 \
    librosa==0.9.2

# Install other Python dependencies from requirements.txt
# It's crucial that your requirements.txt does NOT contain a line that forces numpy>=2.0.0
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