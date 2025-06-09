#!/usr/bin/env python
"""
Pure Python HTTP server to expose video_to_subtitle.py functionalities without using any frameworks
Uses only built-in Python modules: http.server, json, cgi, urllib
Also serves static frontend files
"""

import os
import sys
import json
import uuid
import cgi
import mimetypes
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import the video_to_subtitle functions
from video_to_subtitle import (
    generate_ass_from_video,
    generate_ass_from_video_whisper,
    translate_ass_subtitles,
    check_whisper_availability
)

# Configure folders and allowed extensions
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'outputs')
FRONTEND_FOLDER = os.path.join(PROJECT_ROOT, 'frontend')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Create upload and output folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Common language codes for transcription (AWS Transcribe and Whisper)
TRANSCRIPTION_LANGUAGES = {
    'auto': 'Auto Detect',
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
TRANSLATION_LANGUAGES = {
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

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class VideoSubtitleServer(BaseHTTPRequestHandler):
    """HTTP request handler for VideoSubtitleCleanser API"""
    
    def _set_headers(self, status_code=HTTPStatus.OK, content_type='application/json'):
        """Set response headers with CORS support"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_json_response(self, data, status_code=HTTPStatus.OK):
        """Send JSON response"""
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error_response(self, message, status_code=HTTPStatus.BAD_REQUEST):
        """Send error response"""
        self._send_json_response({'error': message}, status_code)
    
    def _parse_json_body(self):
        """Parse JSON request body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body)
        return {}
    
    def _handle_upload_file(self):
        """Handle file upload request"""
        content_type = self.headers.get('Content-Type', '')
        
        # Check if the request is multipart/form-data
        if not content_type.startswith('multipart/form-data'):
            self._send_error_response('Request must be multipart/form-data')
            return
        
        # Parse the form data
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': content_type
            }
        )
        
        # Check if the file part exists
        if 'file' not in form:
            self._send_error_response('No file part')
            return
        
        file_item = form['file']
        
        # Check if file was selected
        if not file_item.filename:
            self._send_error_response('No file selected')
            return
        
        # Check if file type is allowed
        if not allowed_file(file_item.filename):
            self._send_error_response(f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}')
            return
        
        # Generate a unique filename to avoid collisions
        original_filename = os.path.basename(file_item.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Save the file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        with open(file_path, 'wb') as f:
            f.write(file_item.file.read())
        
        # Send success response
        self._send_json_response({
            'message': 'File uploaded successfully',
            'filename': unique_filename,
            'original_filename': original_filename
        })
    
    def _handle_generate_subtitle(self):
        """Handle subtitle generation request"""
        # Parse request body
        data = self._parse_json_body()
        
        # Validate required parameters
        if not data or 'filename' not in data:
            self._send_error_response('Missing required parameters')
            return
        
        # Get parameters from request
        filename = data.get('filename')
        source_language = data.get('source_language', 'en-US')
        target_language = data.get('target_language', None)
        diarize = data.get('diarize', True)
        grammar = data.get('grammar', False)
        tool = data.get('tool', 'auto')
        detect_text = data.get('detect_text', True)
        
        # Log language settings
        print(f"Source language from request: {source_language}")
        if source_language == 'auto':
            print("Using automatic language detection")

        
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
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(input_path):
            self._send_error_response('Input file not found', HTTPStatus.NOT_FOUND)
            return
        
        # Generate output filename
        output_filename = f"{uuid.uuid4().hex}.ass"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
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
                self._send_json_response({
                    'message': 'Subtitle generated successfully',
                    'filename': output_filename,
                    'translated': bool(translated_file)
                })
            else:
                self._send_error_response('Failed to generate subtitle', HTTPStatus.INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            self._send_error_response(f'Error generating subtitle: {str(e)}', HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def _handle_download_file(self, filename):
        """Handle file download request"""
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            self._send_error_response('File not found', HTTPStatus.NOT_FOUND)
            return
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Send file
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            self._set_headers(content_type=content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(file_content)))
            self.end_headers()
            self.wfile.write(file_content)
        except Exception as e:
            self._send_error_response(f'Error downloading file: {str(e)}', HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def _handle_get_languages(self):
        """Handle get languages request"""
        self._send_json_response({
            'transcription_languages': TRANSCRIPTION_LANGUAGES,
            'translation_languages': TRANSLATION_LANGUAGES
        })
    
    def _handle_health_check(self):
        """Handle health check request"""
        self._send_json_response({
            'status': 'ok',
            'message': 'API server is running',
            'whisper_available': check_whisper_availability(silent=True)
        })
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self._set_headers()
    
    def _serve_static_file(self, file_path):
        """Serve a static file"""
        try:
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
                
            with open(file_path, 'rb') as f:
                content = f.read()
                
            self._set_headers(content_type=content_type)
            self.wfile.write(content)
            return True
        except Exception as e:
            print(f"Error serving static file: {e}")
            return False
    
    def do_GET(self):
        """Handle GET requests"""
        # Parse URL path
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Route to appropriate handler
        if path == '/api/health':
            self._handle_health_check()
        elif path == '/api/languages':
            self._handle_get_languages()
        elif path.startswith('/api/download/'):
            # Extract filename from path
            filename = os.path.basename(path)
            self._handle_download_file(filename)
        else:
            # Serve static files
            if path == '/' or path == '':
                path = '/index.html'
                
            # Map the URL path to the local file path
            local_path = os.path.join(FRONTEND_FOLDER, path.lstrip('/'))
            
            # Check if the file exists and serve it
            if os.path.exists(local_path) and os.path.isfile(local_path):
                self._serve_static_file(local_path)
            else:
                self._send_error_response('Not found', HTTPStatus.NOT_FOUND)
    
    def do_POST(self):
        """Handle POST requests"""
        # Parse URL path
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Route to appropriate handler
        if path == '/api/upload':
            self._handle_upload_file()
        elif path == '/api/generate-subtitle':
            self._handle_generate_subtitle()
        else:
            self._send_error_response('Not found', HTTPStatus.NOT_FOUND)

def run_server(host='0.0.0.0', port=5000):
    """Run the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, VideoSubtitleServer)
    print(f"Starting server on http://{host}:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
