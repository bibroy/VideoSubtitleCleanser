#!/usr/bin/env python
"""
Standalone subtitle extraction utility for VideoSubtitleCleanser
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def ensure_directory_exists(directory_path):
    """Ensure the specified directory exists"""
    Path(directory_path).mkdir(parents=True, exist_ok=True)

def extract_subtitles(input_path, output_path, language=None):
    """
    Extract subtitles from a video file using multiple methods
    
    Args:
        input_path: Path to the input video file
        output_path: Path to save the extracted subtitles
        language: Language code for extraction (optional)
    
    Returns:
        bool: True if extraction was successful, False otherwise
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file does not exist: {input_path}")
        return False
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        ensure_directory_exists(output_dir)
    
    # Get file extension for output
    output_ext = os.path.splitext(output_path)[1].lower()
    if not output_ext:
        output_ext = ".srt"
        output_path = f"{output_path}{output_ext}"
    
    # Try multiple extraction methods
    methods = []
    
    # Method 1: Extract by language if specified
    if language:
        methods.append({
            "name": f"Extract by language tag '{language}'",
            "cmd": [
                "ffmpeg",
                "-i", input_path,
                "-map", f"0:s:m:language:{language}",
                "-c:s", "srt" if output_ext == ".srt" else "copy",
                output_path
            ]
        })
    
    # Method 2: Extract first subtitle stream
    methods.append({
        "name": "Extract first subtitle stream",
        "cmd": [
            "ffmpeg",
            "-i", input_path,
            "-map", "0:s:0",
            "-c:s", "srt" if output_ext == ".srt" else "copy",
            output_path
        ]
    })
    
    # Method 3: Extract using codec copy
    methods.append({
        "name": "Extract using codec copy",
        "cmd": [
            "ffmpeg",
            "-i", input_path,
            "-c:s", "copy",
            output_path
        ]
    })
    
    # Method 4: Extract embedded subtitles
    methods.append({
        "name": "Extract embedded subtitles",
        "cmd": [
            "ffmpeg",
            "-i", input_path,
            "-c:s", "srt" if output_ext == ".srt" else "copy",
            output_path
        ]
    })
    
    # Method 5: Try extracting all subtitle streams
    methods.append({
        "name": "Extract all subtitle streams",
        "cmd": [
            "ffmpeg",
            "-i", input_path,
            "-map", "0:s",
            "-c:s", "srt" if output_ext == ".srt" else "copy",
            output_path
        ]
    })
    
    # Try each method in sequence
    for i, method in enumerate(methods, 1):
        print(f"\nTrying method {i}: {method['name']}")
        print(f"Command: {' '.join(method['cmd'])}")
        
        try:
            result = subprocess.run(
                method["cmd"],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Check if the output file was created and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"\nSuccess! Subtitles extracted to: {output_path}")
                return True
            else:
                print("Command completed but no subtitle file was created.")
        except subprocess.CalledProcessError as e:
            print(f"Failed: {e}")
            print(f"Error output: {e.stderr}")
    
    print("\nAll extraction methods failed.")
    return False

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Extract subtitles from video files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--input", "-i", required=True, help="Path to the input video file")
    parser.add_argument("--output", "-o", required=True, help="Path to save the extracted subtitles")
    parser.add_argument("--language", "-l", help="Language code for extraction (e.g., eng, spa)")
    
    args = parser.parse_args()
    
    success = extract_subtitles(args.input, args.output, args.language)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
