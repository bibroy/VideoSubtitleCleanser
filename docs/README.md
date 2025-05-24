# VideoSubtitleCleanser

An intelligent video subtitle processing system that improves media viewing experience through automated subtitle enhancement, positioning, and synchronization across various video formats.

## Features

- **Subtitle Cleansing and Error Correction**
  - Language consistency maintenance
  - Invalid character removal
  - Extra line removal
  - Grammar and spelling correction

- **Subtitle Positioning Optimization**
  - Automatic repositioning to prevent overlay of text shown in video
  - Font consistency enforcement

- **Timing Synchronization**
  - Sync subtitles with spoken dialogue
  - Fix timing issues and overlaps

- **Speaker Diarization**
  - Identify multiple speakers in videos through AWS Transcribe integration
  - Label dialogues with speaker identifiers and timestamps
  - Fallback to pattern-based speaker detection when AWS is not available

- **Language Translation**
  - Translate subtitles to different languages 
  - Preserve formatting during translation

- **Multiple File Format Support**
  - Subtitle formats: SRT, VTT, SUB, SBV, SMI, SSA, ASS
  - Video formats: MP4, MKV, AVI, MOV, WMV

- **Multiple Interface Options**
  - Web interface with drag-and-drop support
  - Command Line Interface (CLI) for batch processing

## Technology Stack

### Backend
- **Language:** Python 3.8+
- **Framework:** FastAPI
- **AI/ML Services:** AWS AI/ML and Generative AI
- **Processing:** FFmpeg, PySRT
- **NLP:** SpaCy, NLTK, Transformers

### Frontend
- HTML5
- CSS3
- JavaScript

## Getting Started

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed on your system
- Access to AWS services (optional for advanced features)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/VideoSubtitleCleanser.git
cd VideoSubtitleCleanser
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

4. Install the required packages:
```bash
pip install -r requirements.txt
```

5. Run the application:
```bash
cd backend
uvicorn main:app --reload
```

6. Open your browser and navigate to `http://localhost:8000` to access the web interface.

## Usage

### Web Interface

1. Upload a subtitle or video file using the web interface
2. Configure processing options:
   - Select cleansing options
   - Choose positioning preferences
   - Set the output format
   - Enable/disable speaker diarization
3. Click "Process" to start the subtitle enhancement
4. Download the processed file when complete

### CLI Interface

Process a subtitle file:
```bash
python cli.py process --input path/to/subtitle.vtt --output path/to/output.vtt --cleanse --grammar --position
```

Extract and process subtitles from a video:
```bash
python cli.py extract --input path/to/video.mp4 --output path/to/output.vtt --language eng
```

Translate subtitles:
```bash
python cli.py translate --input path/to/subtitle.vtt --output path/to/output.vtt --source auto --target es
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- AWS AI/ML services for advanced processing capabilities
- FFmpeg for video processing
- Open-source NLP libraries for language processing
