# 🚀 AI Lip Sync - Enhanced Edition

An incredibly robust and feature-rich AI-powered lip synchronization application with enterprise-level capabilities.

![AI Lip Sync Banner](https://img.shields.io/badge/AI-Lip%20Sync-red?style=for-the-badge&logo=python)
![Version](https://img.shields.io/badge/Version-2.0-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## ✨ Features

### 🎯 **Dual Processing System**
- **Single File Processing**: Process individual face and audio file pairs
- **Bulk Processing**: Handle multiple file pairs efficiently in batch mode
- **Smart File Management**: Intelligent file pairing and organization

### 🎨 **Advanced UI/UX**
- **Modern Design**: Beautiful dark/light theme with smooth transitions
- **Responsive Layout**: Works perfectly on desktop, tablet, and mobile
- **Drag & Drop Interface**: Intuitive file upload with visual feedback
- **Professional Styling**: Gradient buttons, cards, and animations

### ⚙️ **Quality Presets System**
- **High Quality**: Best output quality with optimized processing
- **Fast Processing**: Speed-optimized with good quality balance
- **Mobile Optimized**: Perfect for mobile devices and smaller files
- **Portrait Mode**: Specialized for vertical/portrait videos
- **Batch Processing**: Optimized for handling multiple files

### 🔧 **Micro-Change Generator**
- **Fine-Tuning Controls**: Adjust lip sync strength, face detection sensitivity
- **Real-time Preview**: See changes before processing
- **Custom Presets**: Save and load your own configurations
- **Parameter Validation**: Smart range checking and optimization

### 📊 **Enterprise Features**
- **Bulk Job Management**: Queue system with progress tracking
- **Preview Generation**: Face thumbnails, audio waveforms, comparisons
- **Error Recovery**: Robust error handling and retry mechanisms
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

### 🎥 **Enhanced Results**
- **Video Statistics**: Duration, resolution, FPS, frame count
- **Before/After Comparison**: Visual comparison of original vs processed
- **Multiple Download Options**: Various formats and quality levels
- **Social Sharing**: Built-in sharing capabilities

## 🛠️ Technology Stack

- **Backend**: Flask, Python 3.10+
- **AI Models**: Wav2Lip (GAN & No-GAN variants)
- **Computer Vision**: OpenCV, Face Detection (S3FD)
- **Audio Processing**: LibROSA, FFmpeg
- **Deep Learning**: PyTorch (CPU optimized)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Custom CSS with Tailwind-inspired utilities
- **Icons**: Font Awesome 6.0

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.10+
FFmpeg
Git
```

### Installation
```bash
# Clone the repository
git clone https://github.com/Ig0tU/ai-lip-sync-enhanced.git
cd ai-lip-sync-enhanced

# Install dependencies
pip install -r requirements.txt

# Download model checkpoints (if not included)
# Place Wav2Lip model files in checkpoints/ directory

# Run the application
python app.py
```

### Access the Application
- **Local**: http://localhost:5000
- **Network**: http://0.0.0.0:5000

## 📁 Project Structure

```
ai-lip-sync-enhanced/
├── app.py                 # Main Flask application
├── bulk_processor.py      # Bulk processing engine
├── preview_generator.py   # Preview and thumbnail generation
├── config_manager.py      # Configuration and presets management
├── inference2.py          # Core AI inference engine
├── audio.py              # Audio processing utilities
├── requirements.txt       # Python dependencies
├── checkpoints/          # AI model files
│   ├── Wav2Lip-SD-GAN.pt
│   └── Wav2Lip-SD-NOGAN.pt
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── bulk_processing.html
│   └── result.html
├── static/               # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
├── models/               # AI model architectures
├── face_detection/       # Face detection modules
├── uploads/              # Temporary upload storage
├── results/              # Generated video outputs
├── temp/                 # Temporary processing files
└── config/               # Configuration files
```

## 🎮 Usage Guide

### Single File Processing
1. **Choose a Preset**: Select from 5 quality presets
2. **Upload Files**: Drag & drop or browse for face and audio files
3. **Fine-tune Settings**: Use micro-change controls for precision
4. **Generate**: Click "Generate Lip-Sync" and wait for processing
5. **Download**: Get your enhanced video with previews

### Bulk Processing
1. **Access Bulk Mode**: Navigate to /bulk or use the bulk panel
2. **Add File Pairs**: Upload multiple face/audio combinations
3. **Configure Settings**: Choose model and quality preset
4. **Start Processing**: Monitor progress with real-time updates
5. **Manage Results**: Download individual or batch results

### Advanced Features
- **Theme Toggle**: Switch between dark and light modes
- **Preview Generation**: See thumbnails and waveforms before processing
- **Progress Tracking**: Real-time updates for long-running jobs
- **Error Recovery**: Automatic retry and error handling

## 🔧 Configuration

### Environment Variables
```bash
NUMBA_CACHE_DIR=/tmp/numba_cache
FLASK_ENV=development
MAX_CONTENT_LENGTH=500MB
```

### Model Configuration
- Place model files in `checkpoints/` directory
- Supported formats: `.pt`, `.pth`
- Models: Wav2Lip-SD-GAN, Wav2Lip-SD-NOGAN

### Quality Presets
Presets are automatically created and can be customized via the web interface or configuration files.

## 📊 Performance

### Benchmarks
- **Single Video**: 2-5 minutes processing time
- **Bulk Processing**: Parallel processing with queue management
- **Memory Usage**: Optimized for CPU-only environments
- **File Support**: Images (JPG, PNG), Videos (MP4, AVI, MOV), Audio (WAV, MP3, AAC)

### Optimization Features
- **Batch Size Control**: Adjustable for memory constraints
- **Resize Factors**: Reduce resolution for faster processing
- **CPU Optimization**: Efficient processing without GPU requirements

## 🛡️ Security & Privacy

- **File Cleanup**: Automatic removal of temporary files
- **Secure Upload**: File type validation and size limits
- **Privacy First**: No data collection or external API calls
- **Local Processing**: All AI processing happens locally

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Code formatting
black . && flake8 .
```

## 📝 API Documentation

### REST Endpoints
- `GET /` - Main interface
- `POST /infer` - Single file processing
- `POST /bulk_infer` - Bulk processing
- `GET /bulk_status/<job_id>` - Job status
- `GET /results/<filename>` - Download results

### WebSocket Support
Real-time progress updates for long-running jobs.

## 🐛 Troubleshooting

### Common Issues
1. **Model Loading Errors**: Ensure model files are in `checkpoints/`
2. **Memory Issues**: Reduce batch sizes in configuration
3. **FFmpeg Errors**: Install FFmpeg system-wide
4. **Permission Errors**: Check file permissions for upload directories

### Debug Mode
```bash
FLASK_DEBUG=1 python app.py
```

## 📈 Roadmap

- [ ] GPU acceleration support
- [ ] Real-time processing mode
- [ ] Advanced face detection options
- [ ] Custom model training interface
- [ ] Cloud deployment templates
- [ ] Mobile app companion

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Wav2Lip**: Original research and model architecture
- **Face Detection**: S3FD implementation
- **UI Inspiration**: Modern web design principles
- **Community**: Contributors and users who make this project better

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Ig0tU/ai-lip-sync-enhanced/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Ig0tU/ai-lip-sync-enhanced/discussions)
- **Documentation**: [Wiki](https://github.com/Ig0tU/ai-lip-sync-enhanced/wiki)

---

**Made with ❤️ by the AI Lip Sync Community**

![Footer](https://img.shields.io/badge/Built%20with-Python%20%7C%20Flask%20%7C%20PyTorch-blue?style=flat-square)
