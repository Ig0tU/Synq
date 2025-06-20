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

# --- START LLVM INSTALLATION FIX ---
# Add Debian's oldstable repository to ensure access to llvm-9-dev if it's considered "older"
# for the default slim image's sources.
# This ensures we can find packages that might not be in the primary/current stable sources.
# It's important to use the correct release name for oldstable (e.g., bullseye, buster).
# For Python 3.9-slim (Debian 11 Bullseye), bullseye is the current stable, so llvm-9-dev should be there.
# Let's ensure the regular apt sources are exhaustive.

RUN apt-get update && apt-get install -y --no-install-recommends \
    lsb-release \
    wget \
    gnupg2 \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add LLVM's official APT repository for a wider range of LLVM versions
# This is generally more reliable for specific LLVM versions.
RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
RUN echo "deb http://apt.llvm.org/bullseye/ llvm-toolchain-bullseye-9 main" >> /etc/apt/sources.list.d/llvm.list \
    && echo "deb-src http://apt.llvm.org/bullseye/ llvm-toolchain-bullseye-9 main" >> /etc/apt/sources.list.d/llvm.list

# Update apt cache again to include the new LLVM repository
RUN apt-get update

# Install specific LLVM 9 development packages
RUN apt-get install -y --no-install-recommends \
    llvm-9-dev \
    llvm-9 \
    llvm-9-runtime \
    clang-9 \
    # Ensure standard build tools and audio libs are present
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
    && rm -rf /var/lib/apt/lists/*

# Set LLVM_CONFIG to the specific version's config script
# This is crucial for llvmlite to find the correct LLVM installation
ENV LLVM_CONFIG=/usr/bin/llvm-config-9
# --- END LLVM INSTALLATION FIX ---


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