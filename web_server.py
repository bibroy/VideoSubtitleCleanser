#!/usr/bin/env python
"""
Robust web server for VideoSubtitleCleanser
Serves both API endpoints and static frontend files
"""

import os
import sys
import json
import uuid
import io
import mimetypes
import urllib.parse
import logging
import email.parser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VideoSubtitleServer')

# Add project root to path to ensure imports work correctly
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the video_to_subtitle functions
try:
    from video_to_subtitle import (
        generate_ass_from_video,
        generate_ass_from_video_whisper,
        translate_ass_subtitles,
        check_whisper_availability
    )
    logger.info("Successfully imported video_to_subtitle functions")
except Exception as e:
    logger.error(f"Error importing video_to_subtitle functions: {e}")
    raise

# Configure folders and allowed extensions
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'outputs')
FRONTEND_FOLDER = os.path.join(PROJECT_ROOT, 'frontend')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Create upload and output folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Common language codes for transcription (AWS Transcribe and Whisper)
TRANSCRIPTION_LANGUAGES = {
    'en-US': 'English (US)',
    'en-GB': 'English (UK)',
    'en-AU': 'English (Australia)',
    'bn-IN': 'Bengali',
    'hi-IN': 'Hindi',
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
    'hi': 'Hindi',
    'bn': 'Bengali',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'pt': 'Portuguese',
    'zh': 'Chinese (Simplified)',
    'ar': 'Arabic',    
    'ru': 'Russian'
}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class VideoSubtitleServer(BaseHTTPRequestHandler):
    """HTTP request handler for VideoSubtitleCleanser API"""
    
    def log_message(self, format, *args):
        """Override log_message to use our logger"""
        logger.info("%s - %s", self.address_string(), format % args)
    
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
        
        # Get the boundary from content-type
        content_type_parts = content_type.split('boundary=')
        if len(content_type_parts) != 2:
            self._send_error_response('Invalid content type format')
            return
            
        boundary = content_type_parts[1].strip()
        
        # Read the content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_error_response('Empty content')
            return
            
        # Read the body
        body = self.rfile.read(content_length)
        
        # Create a parser for multipart/form-data
        parser = email.parser.BytesParser()
        multipart_data = parser.parsebytes(
            b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + body
        )
        
        # Find the file part
        file_part = None
        filename = None
        file_data = None
        
        for part in multipart_data.get_payload():
            if part.get_param('name', header='content-disposition') == 'file':
                file_part = part
                filename = part.get_filename()
                file_data = part.get_payload(decode=True)
                break
        
        # Check if the file part exists
        if not file_part:
            self._send_error_response('No file part')
            return
        
        # Check if file was selected
        if not filename:
            self._send_error_response('No file selected')
            return
        
        # Check if file type is allowed
        if not allowed_file(filename):
            self._send_error_response(f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}')
            return
        
        # Generate a unique filename to avoid collisions
        original_filename = os.path.basename(filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Save the file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Send success response
        self._send_json_response({
            'message': 'File uploaded successfully',
            'filename': unique_filename,
            'original_filename': original_filename
        })
        logger.info(f"File uploaded: {original_filename} -> {unique_filename}")
    
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
        target_language = data.get('target_language')
        
        # Fix for empty target language - only set to None if it's an empty string
        # This preserves explicit null values from the frontend but allows empty strings to be treated as None
        if target_language == "":
            target_language = None
        
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
            logger.info(f"Generating subtitle for {filename} using {tool}")
            logger.info(f"Language parameters: source_language={source_language}, target_language={target_language}")
            logger.info(f"Font style parameters: {font_style}")
            
            if tool == 'whisper':
                logger.info(f"Using Whisper with language: {source_language}")
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
                logger.info(f"Using AWS Transcribe with language: {source_language}")
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
                logger.info(f"Using Auto mode (AWS with Whisper fallback) with language: {source_language}")
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
                logger.info(f"Translating subtitle to {target_language}")
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
                logger.info(f"Subtitle generated successfully: {output_filename}")
            else:
                self._send_error_response('Failed to generate subtitle', HTTPStatus.INTERNAL_SERVER_ERROR)
                logger.error("Failed to generate subtitle")
                
        except Exception as e:
            logger.exception(f"Error generating subtitle: {str(e)}")
            self._send_error_response(f'Error generating subtitle: {str(e)}', HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def _handle_download_file(self, filename):
        """Handle file download request"""
        logger.info(f"Download request received for file: {filename}")
        
        # Clean the filename to prevent path traversal attacks
        clean_filename = os.path.basename(filename)
        file_path = os.path.join(OUTPUT_FOLDER, clean_filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"Download failed: File not found: {file_path}")
            self._send_error_response('File not found', HTTPStatus.NOT_FOUND)
            return
        
        try:
            # Simple approach: read the entire file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Determine content type based on file extension
            content_type = 'application/octet-stream'
            
            # Send headers
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{clean_filename}"')
            self.send_header('Content-Length', str(len(file_content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Send the file content
            self.wfile.write(file_content)
            
            logger.info(f"File {clean_filename} downloaded successfully")
        except Exception as e:
            logger.exception(f"Error downloading file: {str(e)}")
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
            logger.exception(f"Error serving static file: {str(e)}")
            return False
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self._set_headers()
    
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
            # Extract filename from path - remove the prefix
            filename = path.replace('/api/download/', '')
            # Remove query parameters if present
            if '?' in filename:
                filename = filename.split('?')[0]
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

def open_browser(host='localhost', port=5000):
    """Open the browser after a short delay"""
    import webbrowser
    import threading
    import time
    
    def _open_browser():
        time.sleep(2)  # Give the server a moment to start
        url = f"http://{host}:{port}"
        webbrowser.open(url)
        logger.info(f"Browser opened to {url}")
        print(f"Browser opened to {url}")
    
    browser_thread = threading.Thread(target=_open_browser)
    browser_thread.daemon = True
    browser_thread.start()

def run_server(host='0.0.0.0', port=5000, open_browser_automatically=True):
    """Run the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, VideoSubtitleServer)
    
    # Log server startup
    logger.info(f"Starting server on http://{host}:{port}")
    print(f"Starting server on http://{host}:{port}")
    print(f"Serving frontend files from {FRONTEND_FOLDER}")
    
    # Open browser if requested
    if open_browser_automatically:
        open_browser(host='localhost', port=port)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Server error: {str(e)}")
    finally:
        httpd.server_close()
        logger.info("Server closed")

if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run the VideoSubtitleCleanser web server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    args = parser.parse_args()
    
    # Run server
    run_server(host=args.host, port=args.port, open_browser_automatically=not args.no_browser)
