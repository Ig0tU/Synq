# Use an official Python runtime as a parent image (Debian 12 Bookworm)
FROM python:3.9-slim

# Disable Python bytecode, buffer stdout/stderr, pin NumPy <2, and redirect caches
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMPY_EXPLICIT_VERSION=1.23.5 \
    XDG_CACHE_HOME=/app/cache \
    TORCH_HOME=/app/cache/torch \
    LLVM_CONFIG=/usr/bin/llvm-config-14

WORKDIR /app

# Create cache dirs before anything else
RUN mkdir -p /app/cache/torch/hub \
    && chmod -R 777 /app/cache

# Install build dependencies, audio/video libs, and LLVM 14
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

# Pin NumPy to 1.x, then install libs that must compile against it
RUN pip uninstall -y numpy || true && \
    pip install --no-cache-dir numpy==${NUMPY_EXPLICIT_VERSION} && \
    pip install --no-cache-dir \
        llvmlite==0.38.0 \
        numba==0.55.2 \
        resampy==0.3.1 \
        librosa==0.9.2

# Install your other Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create and chmod the uploads/results/checkpoints/temp dirs
RUN mkdir -p uploads results checkpoints temp \
    && chmod -R 777 uploads results checkpoints temp

# Ensure the entire app directory is writable
RUN chmod -R 777 /app

# Expose the inference port
# Expose the inference port
EXPOSE 7860

# Set Flask env
ENV FLASK_APP=app.py \
    FLASK_ENV=production

# Launch with Gunicorn:
#  - gthread: threaded worker class
#  - threads=2: two threads per worker
#  - timeout=600: 10-minute timeout to cover long inferences
CMD ["gunicorn", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--timeout", "600", \
     "--bind", "0.0.0.0:7860", \
     "app:app"]
