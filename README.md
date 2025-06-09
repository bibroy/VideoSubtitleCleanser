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

## Subtitle Format Support

VideoSubtitleCleanser supports multiple subtitle formats to ensure compatibility with various video players:

### WebVTT (.vtt)
- **Best for**: Web players, HTML5 video, Chrome, Firefox, Edge
- **Features**: Full styling support, positioning control, speaker identification
- **Usage**: Default format for web-based video players
- **Command**: `python cli.py process --input input.srt --output output.vtt --format vtt`

### Standard SRT (.srt)
- **Best for**: General compatibility with most video players
- **Features**: Basic text support, widely compatible
- **Usage**: Use when maximum player compatibility is needed
- **Command**: `python cli.py process --input input.vtt --output output.srt --format srt`

### VLC-Compatible SRT (.srt)
- **Best for**: VLC Media Player
- **Features**: ASS override tags for positioning, HTML-style tags for some styling
- **Usage**: Optimized for VLC's subtitle rendering engine
- **Command**: `python cli.py process --input input.vtt --output output.srt --format vlc_srt`

### Advanced SubStation Alpha (.ass)
- **Best for**: PotPlayer, MPC-HC, MPV
- **Features**: Complete styling control, precise positioning, font customization
- **Usage**: Best choice for desktop media players that support advanced styling
- **Basic Command**: `python cli.py process --input input.vtt --output output.ass --format ass`
- **With Font Styling**: `python cli.py process --input input.vtt --output output.ass --format ass --font-name "Calibri" --font-size 28 --bold 1 --primary-color "&H00FFFFFF"`
- **Font Style Options**:
  - `--font-name`: Font family name (default: Arial)
  - `--font-size`: Font size in points (default: 24)
  - `--primary-color`: Text color (default: &H00FFFFFF - white)
  - `--bold`: Bold text (0=off, 1=on)
  - `--italic`: Italic text (0=off, 1=on)
  - `--outline`: Outline thickness (default: 2)
  - `--shadow`: Shadow depth (default: 3)

### Direct Video to ASS Subtitles
- **Features**: Generate ASS subtitles directly from video with all features in one step
  - Font style customization
  - Proper grammar and spelling
  - Multiple language support
  - Speaker diarization with two hyphens (--) for speaker changes
  - Default subtitle position at bottom center
  - Intelligent repositioning to avoid overlaying text in video
- **Command**: `python direct_video_to_ass.py --input video.mp4 --output subtitles.ass --font-name "Arial" --font-size 28 --bold 1`
- **Options**:
  - `--language`: Language code for transcription (default: en-US)
  - `--grammar`: Enable grammar and spelling correction
  - All font style options from above are supported

### Generate All Formats
- **Command**: `python cli.py process --input input.vtt --output output --format both`
- This generates both WebVTT and VLC-compatible SRT files
- For ASS format, use the `--format ass` option with the main CLI as shown above

## Video Player Compatibility

### Web Players
- **HTML5 Video**: Excellent WebVTT support with full styling
- **Video.js**: Great WebVTT support
- **Plyr.io**: Modern player with good WebVTT support
- **JW Player**: Industry standard with WebVTT support

### Desktop Players
- **VLC Media Player**: 
  - Best with VLC-compatible SRT files
  - Configure styling in Tools > Preferences > Subtitles/OSD
  - Limited WebVTT support

- **PotPlayer (Windows)**:
  - Best with ASS format for complete styling control
  - Excellent subtitle customization options
  - Supports intelligent positioning (cue4 at top, others at bottom)
  - Full font styling with customizable colors, sizes, and effects
  - Properly handles bold/italic formatting and shadow/outline effects

- **MPC-HC (Windows)**:
  - Good support for ASS and SRT formats
  - Respects positioning tags

- **MPV Player**:
  - Excellent support for ASS format
  - Good WebVTT support
  - Cross-platform (Windows, macOS, Linux)

## Documentation

For more detailed information, please refer to the following documentation:

- [Architecture](docs/Architecture.md)
- [Running the Application](docs/Run.md)
- [Technology Stack](docs/Techstack.md)

## Tech Stack

### Backend
- Python
- AWS AI/ML and Generative AI services

### Frontend
- HTML
- CSS
- JavaScript

## License

This project is licensed under the MIT License.

## Contributors

- Your Team Name Here
