# VideoSubtitleCleanser

An intelligent video subtitle processing system that improves media viewing experience through automated subtitle enhancement, positioning, and synchronization across various video formats.

## Features

- **Speech-to-Text Subtitle Generation**:
  - Generate WebVTT subtitles directly from video audio tracks
  - Multiple tool options: AWS Transcribe, OpenAI Whisper, or FFmpeg speech detection
  - Automatic fallback system for robust operation
  - Speaker diarization support (identifying different speakers)
- **Subtitle Processing**:
  - Subtitle cleansing and error correction
  - Grammar and spelling correction
  - Invalid character removal
  - Extra line removal
  - Font consistency enforcement
- **Subtitle Optimization**:
  - Subtitle positioning optimization
  - Subtitle timing synchronization with spoken dialogue
  - Repositioning of subtitles to prevent overlay of text shown in video
- **Language Support**:
  - Output subtitle file in different languages according to user's choice
  - Language consistency maintenance
- **Multiple Interfaces**:
  - Web interface for interactive use
  - CLI for batch processing and automation

## Getting Started

### Prerequisites

- Python 3.8+
- FFmpeg
- Web browser (for web interface)

### Installation

1. Clone the repository
2. Install the requirements:
```
pip install -r requirements.txt
```
3. Run the application:
```
cd backend
uvicorn main:app --reload
```
4. Open your browser at http://localhost:8000

## Documentation

For more detailed information, please refer to the following documentation:

- [Architecture](docs/Architecture.md)
- [Running the Application](docs/Run.md)
- [Technology Stack](docs/Techstack.md)

## Tech Stack

### Backend
- Python
- FastAPI
- AWS AI/ML and Generative AI services

### Frontend
- HTML
- CSS
- JavaScript

## License

This project is licensed under the MIT License.

## Contributors

- Your Team Name Here
