# VideoSubtitleCleanser Technology Stack

This document provides a detailed overview of the technologies used in the VideoSubtitleCleanser application.

## Backend Technologies

### Core Framework
- **Python 3.8+**: Primary programming language for the backend
- **FastAPI**: Modern, high-performance web framework for building APIs with Python
- **Uvicorn**: ASGI server for running the FastAPI application
- **Pydantic**: Data validation and settings management using Python type annotations

### Subtitle Processing
- **FFmpeg**: Cross-platform solution for processing multimedia files
- **pysrt**: Python library for manipulating SubRip (.srt) subtitle files
- **chardet**: Character encoding detection library

### Natural Language Processing
- **SpaCy**: Advanced NLP library for language processing tasks
- **NLTK**: Natural Language Toolkit for text analysis
- **language-tool-python**: Python wrapper for LanguageTool, for grammar checking
- **Transformers**: State-of-the-art NLP models from Hugging Face

### Machine Learning & AI
- **AWS AI/ML Services**: Cloud-based AI services for advanced processing
  - **Amazon Transcribe**: For speech-to-text and speaker diarization
  - **Amazon Comprehend**: For language detection and text analysis
  - **Amazon Translate**: For subtitle translation
  - **Amazon SageMaker**: For custom ML models (optional)
- **PyTorch**: Deep learning framework for advanced NLP models

### API & Networking
- **python-multipart**: Support for parsing multipart/form-data
- **WebSockets**: For real-time communication and status updates

### Data Processing
- **pydub**: Audio processing library for working with audio segments
- **numpy**: Numerical processing library

## Frontend Technologies

### Core Technologies
- **HTML5**: Structure of the web application
- **CSS3**: Styling of the web application
- **JavaScript**: Client-side programming language

### UI Components
- **Custom CSS**: Hand-crafted styles for optimal performance
- **Font Awesome**: Icon library for the user interface

## Development & Testing

### Testing
- **Pytest**: Testing framework for Python code
- **Coverage**: Code coverage measurement for Python

### Development Tools
- **python-dotenv**: Loading environment variables from .env files
- **Jinja2**: Template engine for Python

## Deployment & Infrastructure

### Deployment
- **Docker**: Container platform for packaging and deployment
- **Gunicorn**: WSGI HTTP Server for production deployment
- **Nginx**: Web server for reverse proxy and static file serving

### Monitoring & Logging
- **Logging**: Python's built-in logging module
- **Prometheus** (optional): Monitoring and alerting toolkit

## Data Storage

### File Storage
- **Local File System**: For storing uploaded and processed files
- **AWS S3** (optional): For scalable cloud storage

### Task Management
- **In-memory store**: For development and small-scale deployments
- **Redis** (optional): For production task queuing and state management
- **Celery** (optional): Distributed task queue for background processing

## Security

- **CORS Middleware**: Handling Cross-Origin Resource Sharing
- **HTTPS**: For secure communication
- **Input Validation**: Using Pydantic models

## Version Control & Collaboration

- **Git**: Distributed version control system
- **GitHub/GitLab**: Platform for collaboration and code review

## System Requirements

### Minimum Requirements
- **CPU**: 2+ cores
- **RAM**: 4GB+
- **Disk**: 10GB+ free space
- **OS**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **FFmpeg**: Latest stable version

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: SSD with 20GB+ free space
- **Network**: 10Mbps+ connection for cloud service integration

## External Dependencies

### Required
- **FFmpeg**: Must be installed on the system and available in the PATH
- **Python 3.8+**: Required for running the application

### Optional
- **AWS Account**: For using AWS AI/ML services
- **Docker**: For containerized deployment
- **Nginx**: For production deployment

## Package Dependencies

All package dependencies are listed in the `requirements.txt` file and include:

```
fastapi>=0.95.0
uvicorn>=0.21.1
python-multipart>=0.0.6
pydantic>=2.0.0
boto3>=1.26.0
python-dotenv>=1.0.0
ffmpeg-python>=0.2.0
pysrt>=1.1.2
chardet>=5.0.0
spacy>=3.5.0
language-tool-python>=2.7.0
transformers>=4.25.0
torch>=2.0.0
nltk>=3.8
jinja2>=3.1.2
websockets>=11.0.0
pydub>=0.25.1
pytest>=7.3.1
```

## Integration Points

### AWS Services Integration
- Authentication via AWS credentials
- API calls to various AWS services
- S3 for optional file storage

### FFmpeg Integration
- Command-line execution of FFmpeg
- Subtitle extraction and embedding
- Video analysis for positioning

## Performance Considerations

### Optimization Strategies
- Background task processing for long-running operations
- File caching for improved performance
- Efficient subtitle parsing and manipulation
- Asynchronous API endpoints with FastAPI

### Scalability
- Stateless design for horizontal scaling
- Containerization for easy deployment
- Cloud service integration for handling increased load

## Future Technology Considerations

### Planned Enhancements
- **WebRTC**: For real-time video previews
- **WebAssembly**: For client-side processing of small files
- **Rust Components**: For performance-critical processing tasks
- **Custom ML Models**: For specialized subtitle enhancement

### Potential Integrations
- **Content Delivery Networks**: For global file distribution
- **Authentication Providers**: For user management
- **Payment Gateways**: For premium features
