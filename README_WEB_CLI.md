# VideoSubtitleCleanser Web Application and CLI

This document provides instructions for using both the web application and command line interfaces for the VideoSubtitleCleanser tool.

## Table of Contents
- [Installation](#installation)
- [Web Application](#web-application)
  - [Starting the Web Server](#starting-the-web-server)
  - [Using the Web Interface](#using-the-web-interface)
  - [Features](#features)
- [Command Line Interface](#command-line-interface)
  - [Basic Usage](#basic-usage)
  - [Examples](#examples)
- [Configuration](#configuration)
- [Supported Features](#supported-features)

## Installation

1. Ensure you have all the required dependencies installed:

```bash
pip install -r requirements.txt
```

2. Set up your AWS credentials (optional, for AWS Transcribe and Translate features):
   - Create a `.env` file in the project root directory
   - Add your AWS credentials:
   ```
   AWS_ACCESS_KEY=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=your_region
   AWS_S3_BUCKET=your_bucket_name
   ```

## Web Application

### Starting the Web Server

1. Navigate to the project directory:
```bash
cd path/to/VideoSubtitleCleanser
```

2. Start the Python HTTP server:
```bash
python run_web_app.py
```

3. Your web browser should automatically open to:
```
http://localhost:5000
```

4. Alternatively, you can directly run the server script:
```bash
python web_server.py
```

### Using the Web Interface

1. **Upload Video**: Drag and drop your video file or click "Browse Files" to select a video.

2. **Configure Options**:
   - **Transcription Settings**:
     - Source Language: Select the language spoken in the video
     - Transcription Tool: Choose between AWS Transcribe, Whisper, or Auto (tries AWS first, then falls back to Whisper)
     - Speaker Diarization: Enable to identify different speakers
     - Grammar Correction: Enable to improve grammar and punctuation
     - Detect Text in Video: Enable to automatically reposition subtitles to avoid overlaying text in the video

   - **Translation Settings**:
     - Target Language: Select a language to translate the subtitles to (optional)

   - **Font Style Settings**:
     - Font Name: Select the subtitle font
     - Font Size: Set the size of the subtitle text
     - Text Color: Choose the main text color
     - Outline Color: Choose the outline color
     - Background Color: Choose the background color
     - Bold/Italic: Toggle bold or italic formatting
     - Outline Thickness: Set the thickness of the text outline
     - Shadow Depth: Set the depth of the text shadow

3. **Generate Subtitle**: Click the "Generate Subtitle" button to process the video and create the ASS subtitle file.

4. **Download**: Once processing is complete, click "Download Subtitle" to save the generated ASS file.

### Features

- **Intelligent Subtitle Positioning**: Automatically repositions subtitles to avoid overlaying text in the video
- **Speaker Diarization**: Identifies different speakers with two hyphens (--) at the beginning of dialogue
- **Multiple Language Support**: Transcribe and translate subtitles to various languages
- **Complete Font Styling**: Customize the appearance of your subtitles
- **Grammar Correction**: Improve the readability of automatically generated subtitles

## Command Line Interface

### Basic Usage

The command line interface provides the same functionality as the web application:

```bash
python cli_wrapper.py --input video.mp4 [options]
```

### Examples

1. **Basic usage** (generates ASS subtitle with default settings):
```bash
python cli_wrapper.py --input video.mp4
```

2. **With speaker diarization and grammar correction**:
```bash
python cli_wrapper.py --input video.mp4 --diarize --grammar
```

3. **With custom font styling**:
```bash
python cli_wrapper.py --input video.mp4 --font-name "Arial" --font-size 28 --primary-color "&H00FFFFFF" --bold 1
```

4. **With translation**:
```bash
python cli_wrapper.py --input video.mp4 --source-language en-US --target-language bn
```

5. **Specifying transcription tool**:
```bash
python cli_wrapper.py --input video.mp4 --tool whisper
```

### All Available Options

```
--input             Path to the input video file (required)
--output            Path to the output ASS subtitle file (optional)
--source-language   Source language code for transcription (default: en-US)
--target-language   Target language code for translation (optional)
--diarize           Enable speaker diarization
--grammar           Apply grammar correction
--tool              Speech-to-text tool to use (aws, whisper, or auto)
--detect-text       Use Amazon Rekognition to detect text in video and reposition subtitles
--no-detect-text    Disable text detection and automatic subtitle repositioning
--font-name         Font family name (default: Arial)
--font-size         Font size in points (default: 24)
--primary-color     Text color in ASS format (default: &H00FFFFFF - white)
--outline-color     Outline color in ASS format (default: &H00000000 - black)
--back-color        Background color in ASS format (default: &H80000000 - semi-transparent black)
--bold              Bold text (0=off, 1=on, default: 0)
--italic            Italic text (0=off, 1=on, default: 0)
--outline           Outline thickness (default: 2)
--shadow            Shadow depth (default: 3)
--timeout           Timeout in seconds for AWS operations (default: 60)
```

## Configuration

Both the web application and CLI use the same underlying configuration:

1. **AWS Credentials**: Set in the `.env` file or as environment variables
2. **Default Settings**: Can be modified in the respective Python files
3. **Output Directories**:
   - Web application: Creates `uploads` and `outputs` directories
   - CLI: Outputs to the specified path or alongside the input file
4. **Backend Implementation**:
   - Uses only built-in Python modules (http.server, json, cgi, urllib)
   - No external web frameworks required

## Supported Features

- **ASS Subtitle Format**: Full Advanced SubStation Alpha format support
- **Multiple Languages**: Support for various languages through AWS Transcribe and Whisper
- **Translation**: Translation to multiple languages using AWS Translate
- **Font Styling**: Complete customization of subtitle appearance
- **Intelligent Positioning**: Automatic repositioning to avoid overlaying text in video
- **Speaker Diarization**: Identification of different speakers in the dialogue
- **Grammar Correction**: Improved readability through grammar and punctuation fixes
