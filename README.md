# VideoSubtitleCleanser

An intelligent video subtitle processing system that improves media viewing experience through automated subtitle enhancement, positioning, and synchronization across various video formats.

## Features

- Subtitle cleansing and error correction
- Output subtitle file can be of different languages according to the user's choice
- Language consistency maintenance
- Invalid character removal
- Extra line removal
- Grammar and spelling correction
- Subtitle positioning optimization
- Subtitle timing synchronization with spoken dialogue
- Font consistency enforcement
- Repositioning of subtitle to prevent overlay of any text shown in video
- Speaker diarization - Identifying multiple speakers in the video using AWS Transcribe (with fallback to pattern detection) and labeling dialogues with speaker identifiers
- Support for video and subtitle file processing
- Multiple interface options (CLI and Web)

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
