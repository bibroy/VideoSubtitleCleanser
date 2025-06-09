#!/usr/bin/env python
"""
Flask API server to expose video_to_subtitle.py functionalities
"""

import os
import sys
import uuid
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import the video_to_subtitle functions
from video_to_subtitle import (
    generate_ass_from_video,
    generate_ass_from_video_whisper,
    translate_ass_subtitles,
    check_whisper_availability
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'outputs')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Create upload and output folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload size

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "API server is running",
        "whisper_available": check_whisper_availability(silent=True)
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload video file endpoint"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # Check if user did not select a file
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file type is allowed
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Generate a unique filename to avoid collisions
    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Save the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    return jsonify({
        'message': 'File uploaded successfully',
        'filename': unique_filename,
        'original_filename': original_filename
    })

@app.route('/api/generate-subtitle', methods=['POST'])
def generate_subtitle():
    """Generate subtitle endpoint"""
    data = request.json
    
    # Validate required parameters
    if not data or 'filename' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Get parameters from request
    filename = data.get('filename')
    source_language = data.get('source_language', 'en-US')
    target_language = data.get('target_language', None)
    diarize = data.get('diarize', True)
    grammar = data.get('grammar', False)
    tool = data.get('tool', 'auto')
    detect_text = data.get('detect_text', True)
    
    # Font style parameters
    font_style = {
        'font_name': data.get('font_name', 'Arial'),
        'font_size': int(data.get('font_size', 24)),
        'primary_color': data.get('primary_color', '&H00FFFFFF'),
        'outline_color': data.get('outline_color', '&H00000000'),
        'back_color': data.get('back_color', '&H80000000'),
        'bold': int(data.get('bold', 0)),
        'italic': int(data.get('italic', 0)),
        'outline': int(data.get('outline', 2)),
        'shadow': int(data.get('shadow', 3))
    }
    
    # Validate input file exists
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'error': 'Input file not found'}), 404
    
    # Generate output filename
    output_filename = f"{uuid.uuid4().hex}.ass"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    try:
        # Generate subtitle based on selected tool
        success = False
        
        if tool == 'whisper':
            success = generate_ass_from_video_whisper(
                input_path,
                output_path,
                source_language,
                diarize,
                grammar,
                font_style,
                detect_text=detect_text
            )
        elif tool == 'aws':
            success = generate_ass_from_video(
                input_path,
                output_path,
                source_language,
                diarize,
                grammar,
                font_style,
                use_aws=True,
                use_whisper=False,
                detect_text=detect_text
            )
        else:  # auto
            success = generate_ass_from_video(
                input_path,
                output_path,
                source_language,
                diarize,
                grammar,
                font_style,
                use_aws=True,
                use_whisper=True,
                detect_text=detect_text
            )
        
        # Apply translation if needed
        translated_file = None
        if success and target_language:
            translated_file = translate_ass_subtitles(
                output_path,
                source_language,
                target_language
            )
            if translated_file:
                # Use the translated file as the output
                output_filename = os.path.basename(translated_file)
        
        if success:
            return jsonify({
                'message': 'Subtitle generated successfully',
                'filename': output_filename,
                'translated': bool(translated_file)
            })
        else:
            return jsonify({'error': 'Failed to generate subtitle'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Error generating subtitle: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download generated subtitle file"""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/api/languages', methods=['GET'])
def get_languages():
    """Get available languages for transcription and translation"""
    # Common language codes for transcription (AWS Transcribe and Whisper)
    transcription_languages = {
        'en-US': 'English (US)',
        'en-GB': 'English (UK)',
        'en-AU': 'English (Australia)',
        'fr-FR': 'French',
        'de-DE': 'German',
        'es-ES': 'Spanish',
        'it-IT': 'Italian',
        'ja-JP': 'Japanese',
        'ko-KR': 'Korean',
        'pt-BR': 'Portuguese (Brazil)',
        'zh-CN': 'Chinese (Mandarin)'
    }
    
    # Common language codes for translation (AWS Translate)
    translation_languages = {
        'en': 'English',
        'fr': 'French',
        'de': 'German',
        'es': 'Spanish',
        'it': 'Italian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'pt': 'Portuguese',
        'zh': 'Chinese (Simplified)',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'bn': 'Bengali',
        'ru': 'Russian'
    }
    
    return jsonify({
        'transcription_languages': transcription_languages,
        'translation_languages': translation_languages
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
