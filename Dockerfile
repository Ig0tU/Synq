FROM python:3.9-slim-bullseye

# Disable Numba’s JIT cache (avoids Librosa/Numba caching errors)
ENV NUMBA_DISABLE_JIT=1

# Python & app environment
ENV PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git curl \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 \
    build-essential \
    llvm llvm-dev clang-11 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and pre‑install numpy
RUN pip install --upgrade pip 
# && pip install numpy==1.21.6

# Install Gunicorn + Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p cache uploads results checkpoints temp \
 && chmod -R 777 cache uploads results checkpoints temp

# Copy app code
COPY . .

EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
