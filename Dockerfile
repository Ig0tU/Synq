# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_DISABLE_JIT=1

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install build dependencies for numba/llvmlite (LLVM and Clang), including specific dev libraries
# This uses the default available LLVM/Clang versions for Debian Bookworm
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        llvm \
        clang \
        # Essential build tools
        build-essential \
        # Libraries for llvmlite and cffi
        libedit-dev \
        libffi-dev \
        # Python dev headers, often needed for compiling Python extensions
        python3-dev \
        # --- NEW: Install OpenCV dependencies for graphical libraries ---
        libgl1-mesa-glx \
        libsm6 \
        libxrender1 \
        # --- End NEW ---
        && \
    rm -rf /var/lib/apt/lists/*

# Set LLVM_CONFIG environment variable *before* installing numba/llvmlite
# Use the version that apt-get install llvm provides (likely llvm-config-14 for Bookworm)
ENV LLVM_CONFIG=/usr/bin/llvm-config-14

# Install numpy first, as numba/llvmlite depend on it for building
# It's explicitly installed here to ensure it's available for numba's build process.
RUN pip install --no-cache-dir numpy==1.22.4

# Install the rest of the dependencies
# REMOVED: && python -m spacy download en_core_web_sm
RUN pip install --no-cache-dir -r requirements.txt

# --- NEW: Move COPY . /app/ here, after all apt-get and pip installs ---
# Copy the rest of the application code to /app
# This should be done AFTER all dependencies are installed
COPY . /app/
# --- End NEW ---

# Create necessary directories with appropriate permissions
RUN mkdir -p /app/cache /app/uploads /app/results /app/checkpoints /app/temp \
 && chmod -R 777 /app/cache /app/uploads /app/results /app/checkpoints /app/temp

# Ensure all relevant directories have the correct permissions (redundant for /app itself if contents are copied later)
# This line is now effectively ensuring any newly created files/directories *after* the initial copy also have permissions.
RUN chmod -R 777 /app

# Disable Numba's on-disk caching (often problematic in containers) - already present but keeping it for clarity
ENV NUMBA_DISABLE_PER_FILE_CACHE=1

# Expose the port the app runs on
EXPOSE 7860

# Set environment variables for Flask
ENV FLASK_APP=app.py \
    FLASK_ENV=production

# Command to run the application
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:7860", "--timeout", "120", "app:app"]