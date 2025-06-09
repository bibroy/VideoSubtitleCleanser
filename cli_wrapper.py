#!/usr/bin/env python
"""
Command line wrapper for video_to_subtitle.py functionalities
"""

import os
import sys
import argparse
from pathlib import Path

# Import the video_to_subtitle functions
from video_to_subtitle import (
    generate_ass_from_video,
    generate_ass_from_video_whisper,
    translate_ass_subtitles,
    check_whisper_availability
)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Generate ASS subtitle files from video with customizable features",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument("--input", required=True, help="Path to the input video file")
    parser.add_argument("--output", help="Path to the output ASS subtitle file")
    
    # Optional arguments
    parser.add_argument("--source-language", default="en-US", 
                      help="Source language code for transcription (e.g., en-US, fr-FR, de-DE)")
    parser.add_argument("--target-language", 
                      help="Target language code for translation (e.g., bn for Bengali, hi for Hindi)")
    parser.add_argument("--diarize", action="store_true", help="Enable speaker diarization")
    parser.add_argument("--grammar", action="store_true", help="Apply grammar correction")
    parser.add_argument("--tool", default="auto", choices=["aws", "whisper", "auto"], 
                      help="Speech-to-text tool to use (aws, whisper, or auto)")
    parser.add_argument("--detect-text", action="store_true", default=True,
                      help="Use Amazon Rekognition to detect text in video and reposition subtitles")
    parser.add_argument("--no-detect-text", action="store_false", dest="detect_text",
                      help="Disable text detection and automatic subtitle repositioning")
    
    # Font style parameters
    parser.add_argument("--font-name", default="Arial", help="Font family name (default: Arial)")
    parser.add_argument("--font-size", type=int, default=24, help="Font size in points (default: 24)")
    parser.add_argument("--primary-color", default="&H00FFFFFF", help="Text color in ASS format (default: &H00FFFFFF - white)")
    parser.add_argument("--outline-color", default="&H00000000", help="Outline color in ASS format (default: &H00000000 - black)")
    parser.add_argument("--back-color", default="&H80000000", help="Background color in ASS format (default: &H80000000 - semi-transparent black)")
    parser.add_argument("--bold", type=int, choices=[0, 1], default=0, help="Bold text (0=off, 1=on, default: 0)")
    parser.add_argument("--italic", type=int, choices=[0, 1], default=0, help="Italic text (0=off, 1=on, default: 0)")
    parser.add_argument("--outline", type=int, default=2, help="Outline thickness (default: 2)")
    parser.add_argument("--shadow", type=int, default=3, help="Shadow depth (default: 3)")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds for AWS operations")
    
    args = parser.parse_args()
    
    # Set timeout environment variable from command line argument
    if args.timeout:
        os.environ["AWS_TIMEOUT"] = str(args.timeout)
    
    # Create font style dictionary
    font_style = {
        "font_name": args.font_name,
        "font_size": args.font_size,
        "primary_color": args.primary_color,
        "outline_color": args.outline_color,
        "back_color": args.back_color,
        "bold": args.bold,
        "italic": args.italic,
        "outline": args.outline,
        "shadow": args.shadow
    }
    
    # Check if output path is provided, if not, generate one
    if not args.output:
        input_path = Path(args.input)
        output_path = input_path.with_suffix('.ass')
        args.output = str(output_path)
    
    # Generate subtitle based on selected tool
    success = False
    
    if args.tool == 'whisper':
        print("Using Whisper transcription as requested...")
        success = generate_ass_from_video_whisper(
            args.input,
            args.output,
            args.source_language,
            args.diarize,
            args.grammar,
            font_style,
            detect_text=args.detect_text
        )
    elif args.tool == 'aws':
        print("Using AWS Transcribe as requested...")
        success = generate_ass_from_video(
            args.input,
            args.output,
            args.source_language,
            args.diarize,
            args.grammar,
            font_style,
            use_aws=True,
            use_whisper=False,
            detect_text=args.detect_text
        )
    else:  # auto
        print("Using automatic tool selection (AWS with Whisper fallback)...")
        success = generate_ass_from_video(
            args.input,
            args.output,
            args.source_language,
            args.diarize,
            args.grammar,
            font_style,
            use_aws=True,
            use_whisper=True,
            detect_text=args.detect_text
        )
    
    # Apply translation if needed
    if success and args.target_language:
        print(f"\nApplying translation to {args.target_language}...")
        translated_file = translate_ass_subtitles(
            args.output,
            args.source_language,
            args.target_language
        )
        if translated_file:
            print(f"Successfully created translated subtitle file: {translated_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
