import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Union, Optional, Any

def ensure_directory_exists(directory_path: Union[str, Path]) -> None:
    """
    Ensure that a directory exists, creating it if necessary
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)

def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    Get the file extension from a path
    """
    return os.path.splitext(file_path)[1].lower()

def is_valid_subtitle_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is a valid subtitle file based on extension
    """
    valid_extensions = ['.srt', '.vtt', '.sub', '.sbv', '.smi', '.ssa', '.ass']
    return get_file_extension(file_path) in valid_extensions

def is_valid_video_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is a valid video file based on extension
    """
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv']
    return get_file_extension(file_path) in valid_extensions

def has_ffmpeg() -> bool:
    """
    Check if FFmpeg is installed on the system
    """
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False

def format_timestamp(milliseconds: int) -> str:
    """
    Format milliseconds into SRT timestamp format (HH:MM:SS,mmm)
    """
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def parse_timestamp(timestamp: str) -> int:
    """
    Parse SRT timestamp format (HH:MM:SS,mmm) into milliseconds
    """
    if not timestamp:
        return 0
        
    # Handle both comma and period as decimal separators
    timestamp = timestamp.replace(',', '.')
    
    parts = timestamp.split(':')
    if len(parts) != 3:
        return 0
        
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        
        second_parts = parts[2].split('.')
        seconds = int(second_parts[0])
        milliseconds = int(second_parts[1]) if len(second_parts) > 1 else 0
        
        total_milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_milliseconds
    except ValueError:
        return 0

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters
    """
    # Remove characters that are invalid in filenames
    sanitized = re.sub(r'[\\/*?:"<>|]', '', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    return sanitized

def get_mime_type(file_path: Union[str, Path]) -> str:
    """
    Get the MIME type of a file based on its extension
    """
    extension = get_file_extension(file_path)
    
    mime_types = {
        '.srt': 'application/x-subrip',
        '.vtt': 'text/vtt',
        '.sub': 'text/plain',
        '.sbv': 'text/plain',
        '.smi': 'text/plain',
        '.ssa': 'text/plain',
        '.ass': 'text/plain',
        '.mp4': 'video/mp4',
        '.mkv': 'video/x-matroska',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv'
    }
    
    return mime_types.get(extension, 'application/octet-stream')
