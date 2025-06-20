# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables for Python and Numba
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/tmp/numba_cache

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install build dependencies and LLVM components from Debian's default repos
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
        # Try to install LLVM 9 directly from Debian's repositories
        # clang-9 often pulls in the necessary llvm-9-dev components
        clang-9 \
        llvm-9-dev \
        llvm-9-runtime \
        # Sometimes just 'llvm' and 'libllvm-9-ocaml-dev' or similar
        # is what's needed, but let's be specific for 9.
        # If llvm-9-dev still fails, then try just clang-9.
        && rm -rf /var/lib/apt/lists/*

# Set LLVM_CONFIG to the specific version's config script
# For Debian's llvm-9-dev, this path should be correct.
ENV LLVM_CONFIG=/usr/bin/llvm-config-9


# Explicitly install compatible versions of core audio/Numba stack
# Order matters: numpy -> llvmlite -> numba -> resampy -> librosa
RUN pip install --no-cache-dir \
    numpy==1.22.4 \
    llvmlite==0.31.0 \
    numba==0.48.0 \
    resampy==0.2.2 \
    librosa==0.8.1

# Install other Python dependencies from requirements.txt
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