FROM python:3.9-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    # Ensuring the llvm-config from clang-11 is used:
    LLVM_CONFIG=/usr/bin/llvm-config

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg git curl \
      libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 \
      build-essential \
      llvm llvm-dev clang-11 \
    && rm -rf /var/lib/apt/lists/*

# Pip setup
RUN pip install --upgrade pip && pip install numpy==1.21.6
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
