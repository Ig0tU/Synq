#!/bin/bash
set -e

# Function to check for command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python 3
if ! command_exists python3; then
    echo "Error: Python 3 is not installed. Please install Python 3.10+."
    exit 1
fi

# Check for FFmpeg
if ! command_exists ffmpeg; then
    echo "Error: FFmpeg is not installed. Please install FFmpeg."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment activation script not found."
    exit 1
fi

# Upgrade pip
pip install --upgrade pip

# Ensure compatible numpy version (Wav2Lip requires < 2.0)
echo "Installing compatible numpy version..."
pip install "numpy<2.0"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for Face Detection Model
SFD_DIR="face_detection/detection/sfd"
SFD_MODEL="$SFD_DIR/s3fd.pth"
SFD_BACKUP="$SFD_DIR/s3fd-619a316812.pth"

if [ ! -f "$SFD_MODEL" ]; then
    if [ -f "$SFD_BACKUP" ]; then
        echo "Renaming $SFD_BACKUP to $SFD_MODEL..."
        cp "$SFD_BACKUP" "$SFD_MODEL"
    else
        echo "Warning: Face detection model not found at $SFD_MODEL."
        echo "Please download it from https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth"
        echo "and save it to $SFD_MODEL"
    fi
else
    echo "Face detection model found."
fi

# Check for Wav2Lip Checkpoints
CHECKPOINTS_DIR="checkpoints"
mkdir -p "$CHECKPOINTS_DIR"
GAN_MODEL="$CHECKPOINTS_DIR/Wav2Lip-SD-GAN.pt"
NOGAN_MODEL="$CHECKPOINTS_DIR/Wav2Lip-SD-NOGAN.pt"

if [ ! -f "$GAN_MODEL" ] && [ ! -f "$NOGAN_MODEL" ]; then
    echo "Warning: No Wav2Lip model checkpoints found in $CHECKPOINTS_DIR."
    echo "Please download Wav2Lip-SD-GAN.pt or Wav2Lip-SD-NOGAN.pt and place them in $CHECKPOINTS_DIR."
else
    echo "Wav2Lip model checkpoints found."
fi

# Create necessary directories
echo "Creating application directories..."
mkdir -p uploads results temp config

# Run the application
echo "Starting application..."
python app.py
