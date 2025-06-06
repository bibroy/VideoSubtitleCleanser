#!/usr/bin/env python
"""
CLI interface for VideoSubtitleCleanser
"""
import argparse
import os
import sys
import uuid
from pathlib import Path
import json

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.services import processing_service, subtitle_service, translation_service
from backend.models.schema import ProcessingOptions
from backend.utils.file_utils import ensure_directory_exists, is_valid_subtitle_file, is_valid_video_file

def setup_argparse():
    """Set up the argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description="VideoSubtitleCleanser - Enhance and process subtitle files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
      # Process command
    process_parser = subparsers.add_parser("process", help="Process a subtitle file")
    process_parser.add_argument("--input", required=True, help="Path to the input subtitle file")
    process_parser.add_argument("--output", help="Path to the output subtitle file")
    process_parser.add_argument("--format", default="both", choices=["srt", "vtt", "both", "vlc_srt", "ass", "sub", "sbv", "smi", "ssa"], 
                               help="Output format. Use 'both' to generate both WebVTT and VLC-compatible SRT files, 'ass' for PotPlayer-compatible Advanced SubStation Alpha format")
    
    # Font style parameters for ASS format
    font_style_group = process_parser.add_argument_group('ASS Font Style Options (only used with --format ass)')
    font_style_group.add_argument("--font-name", default="Arial", help="Font family name (default: Arial)")
    font_style_group.add_argument("--font-size", type=int, default=24, help="Font size in points (default: 24)")
    font_style_group.add_argument("--primary-color", default="&H00FFFFFF", help="Text color in ASS format (default: &H00FFFFFF - white)")
    font_style_group.add_argument("--outline-color", default="&H00000000", help="Outline color in ASS format (default: &H00000000 - black)")
    font_style_group.add_argument("--back-color", default="&H80000000", help="Background color in ASS format (default: &H80000000 - semi-transparent black)")
    font_style_group.add_argument("--bold", type=int, choices=[0, 1], default=0, help="Bold text (0=off, 1=on, default: 0)")
    font_style_group.add_argument("--italic", type=int, choices=[0, 1], default=0, help="Italic text (0=off, 1=on, default: 0)")
    font_style_group.add_argument("--outline", type=int, default=2, help="Outline thickness (default: 2)")
    font_style_group.add_argument("--shadow", type=int, default=3, help="Shadow depth (default: 3)")
    process_parser.add_argument("--cleanse", action="store_true", help="Cleanse errors and fix formatting")
    process_parser.add_argument("--grammar", action="store_true", help="Correct grammar and spelling")
    process_parser.add_argument("--no-position", action="store_true", help="Disable position optimization")
    process_parser.add_argument("--video", help="Path to the associated video file (required for position optimization)")
    process_parser.add_argument("--diarize", action="store_true", help="Enable speaker diarization")
    process_parser.add_argument("--use-aws", action="store_true", help="Use AWS Transcribe for speaker diarization (requires AWS credentials)")
    process_parser.add_argument("--max-speakers", type=int, default=10, help="Maximum number of speakers to identify")
    process_parser.add_argument("--target-language", help="Translate to target language")
    process_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract embedded subtitles from a video file")
    extract_parser.add_argument("--input", required=True, help="Path to the input video file")
    extract_parser.add_argument("--output", help="Path to the output subtitle file")
    extract_parser.add_argument("--language", default="eng", help="Language code for extraction")
    extract_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    # Transcribe command
    transcribe_parser = subparsers.add_parser("transcribe", help="Generate subtitles from video using speech-to-text")
    transcribe_parser.add_argument("--input", required=True, help="Path to the input video file")
    transcribe_parser.add_argument("--output", help="Path to the output subtitle file")
    transcribe_parser.add_argument("--language", default="en-US", help="Language code for transcription (e.g., en-US, fr-FR)")
    transcribe_parser.add_argument("--format", default="webvtt", choices=["webvtt", "srt", "ass"], 
                                 help="Output subtitle format (webvtt, srt, or ass)")
    
    # Font style parameters for ASS format when transcribing
    transcribe_font_style_group = transcribe_parser.add_argument_group('ASS Font Style Options (only used with --format ass)')
    transcribe_font_style_group.add_argument("--font-name", default="Arial", help="Font family name (default: Arial)")
    transcribe_font_style_group.add_argument("--font-size", type=int, default=24, help="Font size in points (default: 24)")
    transcribe_font_style_group.add_argument("--primary-color", default="&H00FFFFFF", help="Text color in ASS format (default: &H00FFFFFF - white)")
    transcribe_font_style_group.add_argument("--outline-color", default="&H00000000", help="Outline color in ASS format (default: &H00000000 - black)")
    transcribe_font_style_group.add_argument("--back-color", default="&H80000000", help="Background color in ASS format (default: &H80000000 - semi-transparent black)")
    transcribe_font_style_group.add_argument("--bold", type=int, choices=[0, 1], default=0, help="Bold text (0=off, 1=on, default: 0)")
    transcribe_font_style_group.add_argument("--italic", type=int, choices=[0, 1], default=0, help="Italic text (0=off, 1=on, default: 0)")
    transcribe_font_style_group.add_argument("--outline", type=int, default=2, help="Outline thickness (default: 2)")
    transcribe_font_style_group.add_argument("--shadow", type=int, default=3, help="Shadow depth (default: 3)")
    transcribe_parser.add_argument("--tool", default="auto", choices=["aws", "whisper", "ffmpeg", "auto"], 
                                 help="Speech-to-text tool to use (aws, whisper, ffmpeg, or auto)")
    transcribe_parser.add_argument("--grammar", action="store_true", help="Correct grammar and spelling")
    transcribe_parser.add_argument("--diarize", action="store_true", help="Enable speaker diarization")
    transcribe_parser.add_argument("--max-speakers", type=int, default=10, help="Maximum number of speakers to identify")
    transcribe_parser.add_argument("--no-position", action="store_true", help="Disable position optimization")
    transcribe_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    # Translate command
    translate_parser = subparsers.add_parser("translate", help="Translate a subtitle file")
    translate_parser.add_argument("--input", required=True, help="Path to the input subtitle file")
    translate_parser.add_argument("--output", help="Path to the output subtitle file")
    translate_parser.add_argument("--source", default="auto", help="Source language (auto for auto-detect)")
    translate_parser.add_argument("--target", required=True, help="Target language code")
    translate_parser.add_argument("--quality", default="standard", choices=["standard", "premium"], 
                                help="Translation quality")
    translate_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a subtitle file")
    analyze_parser.add_argument("--input", required=True, help="Path to the input subtitle file")
    analyze_parser.add_argument("--output", help="Path to the output analysis JSON file")
    analyze_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    return parser

def process_subtitle_file(args):
    """Process a subtitle file with the given options"""
    print(f"Processing subtitle file: {args.input}")
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file does not exist: {args.input}")
        return 1
    
    if not is_valid_subtitle_file(args.input):
        print(f"Error: Not a valid subtitle file: {args.input}")
        return 1
    
    # Prepare output path
    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        # Set appropriate extension based on format
        if args.format == "ass":
            extension = "ass"
        elif args.format == "vtt":
            extension = "vtt"
        elif args.format in ["srt", "vlc_srt"]:
            extension = "srt"
        elif args.format == "both":
            extension = "vtt"  # Default extension for 'both' format
        else:
            extension = args.format
        output_path = f"{base_name}_processed.{extension}"
    else:
        # If output path is provided but has no extension, add the appropriate one
        _, ext = os.path.splitext(output_path)
        if not ext:
            if args.format == "ass":
                output_path = f"{output_path}.ass"
            elif args.format == "vtt":
                output_path = f"{output_path}.vtt"
            elif args.format in ["srt", "vlc_srt"]:
                output_path = f"{output_path}.srt"
            # For 'both' format, don't add extension as it will create multiple files
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Create required directories
    ensure_directory_exists("data/uploads")
    ensure_directory_exists("data/processed")
    
    # Copy input to uploads directory
    input_ext = os.path.splitext(args.input)[1]
    task_file_path = f"data/uploads/{task_id}{input_ext}"
    
    if args.verbose:
        print(f"Copying input file to: {task_file_path}")
    
    with open(args.input, "rb") as src, open(task_file_path, "wb") as dst:
        dst.write(src.read())
    
    # Handle video file if provided (for position optimization)
    if args.video and os.path.exists(args.video):
        if not is_valid_video_file(args.video):
            print(f"Warning: Not a valid video file: {args.video}")
        else:
            # Create videos directory
            ensure_directory_exists("data/videos")
            
            # Copy video to videos directory with task_id
            video_ext = os.path.splitext(args.video)[1]
            video_task_path = f"data/videos/{task_id}{video_ext}"
            
            if args.verbose:
                print(f"Copying video file to: {video_task_path}")
            
            with open(args.video, "rb") as src, open(video_task_path, "wb") as dst:
                dst.write(src.read())
                
            if args.verbose and not args.no_position:
                print("Video file will be used for position optimization with AWS Rekognition")
    elif not args.no_position:
        print("Warning: No video file provided. Position optimization will be skipped.")
        
    # Create processing options
    options = {
        "cleanse_errors": args.cleanse,
        "correct_grammar": args.grammar,
        "remove_invalid_chars": True,
        "correct_timing": True,
        "optimize_position": not args.no_position,
        "target_language": args.target_language,
        "diarize_speakers": args.diarize,
        "use_aws_transcribe": args.use_aws if args.diarize else False,
        "max_speakers": args.max_speakers,
        "enforce_font_consistency": True,
        "remove_duplicate_lines": True,
        "output_format": args.format
    }
    
    # Add font style options for ASS format
    if args.format == "ass":
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
        options["font_style"] = font_style
    
    if args.verbose:
        print("Processing options:")
        print(json.dumps(options, indent=2))
    
    # Process the subtitle
    print("Processing subtitle...")
    processing_service.process_subtitle(task_id, options)
    
    # Wait for completion
    import time
    max_wait = 60  # Maximum wait time in seconds
    wait_time = 0
    while wait_time < max_wait:
        status = subtitle_service.get_task_status(task_id)
        if status["status"] == "completed":
            processed_path = status.get("output_path")
            if processed_path and os.path.exists(processed_path):
                print(f"Processing completed successfully.")
                
                # Copy to output path
                with open(processed_path, "rb") as src, open(output_path, "wb") as dst:
                    dst.write(src.read())
                
                print(f"Processed subtitle saved to: {output_path}")
                return 0
            break
        elif status["status"] == "error":
            print(f"Processing failed: {status.get('message', 'Unknown error')}")
            return 1
        
        print("Processing... Please wait.")
        time.sleep(3)
        wait_time += 3
    
    print("Timeout waiting for processing to complete. The operation may still be running in the background.")
    return 1

def extract_subtitles(args):
    """Extract subtitles from a video file"""
    print(f"Extracting subtitles from video: {args.input}")
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file does not exist: {args.input}")
        return 1
    
    if not is_valid_video_file(args.input):
        print(f"Error: Not a valid video file: {args.input}")
        return 1
      # Prepare output path
    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_path = f"{base_name}_extracted.vtt"
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Create required directories
    ensure_directory_exists("data/videos")
    ensure_directory_exists("data/uploads")
    
    # Copy input to videos directory
    input_ext = os.path.splitext(args.input)[1]
    task_file_path = f"data/videos/{task_id}{input_ext}"
    
    if args.verbose:
        print(f"Copying input file to: {task_file_path}")
    
    with open(args.input, "rb") as src, open(task_file_path, "wb") as dst:
        dst.write(src.read())
    
    # Extract the subtitles
    print(f"Extracting subtitles with language: {args.language}...")
    processing_service.extract_subtitles(task_id, args.language)
    
    # Wait for completion
    import time
    max_wait = 60  # Maximum wait time in seconds
    wait_time = 0
    while wait_time < max_wait:
        status = subtitle_service.get_task_status(task_id)
        if status["status"] == "extracted":
            extracted_path = status.get("subtitle_path")
            if extracted_path and os.path.exists(extracted_path):
                print(f"Extraction completed successfully.")
                
                # Copy to output path
                with open(extracted_path, "rb") as src, open(output_path, "wb") as dst:
                    dst.write(src.read())
                
                print(f"Extracted subtitle saved to: {output_path}")
                return 0
            break
        elif status["status"] == "error":
            print(f"Extraction failed: {status.get('message', 'Unknown error')}")
            return 1
        
        print("Extracting... Please wait.")
        time.sleep(3)
        wait_time += 3
    
    print("Timeout waiting for extraction to complete. The operation may still be running in the background.")
    return 1

def translate_subtitle(args):
    """Translate a subtitle file"""
    print(f"Translating subtitle file: {args.input}")
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file does not exist: {args.input}")
        return 1
    
    if not is_valid_subtitle_file(args.input):
        print(f"Error: Not a valid subtitle file: {args.input}")
        return 1
    
    # Prepare output path
    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_path = f"{base_name}_{args.target}.srt"
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Create required directories
    ensure_directory_exists("data/uploads")
    ensure_directory_exists("data/processed")
    
    # Copy input to uploads directory
    input_ext = os.path.splitext(args.input)[1]
    task_file_path = f"data/uploads/{task_id}{input_ext}"
    
    if args.verbose:
        print(f"Copying input file to: {task_file_path}")
    
    with open(args.input, "rb") as src, open(task_file_path, "wb") as dst:
        dst.write(src.read())
    
    # Translate the subtitle
    print(f"Translating from {args.source} to {args.target}...")
    source_lang = None if args.source == "auto" else args.source
    
    translation_service.translate_subtitle(
        task_id=task_id,
        source_language=source_lang,
        target_language=args.target,
        quality=args.quality
    )
    
    # Wait for completion
    import time
    max_wait = 60  # Maximum wait time in seconds
    wait_time = 0
    while wait_time < max_wait:
        status = subtitle_service.get_task_status(task_id)
        if status["status"] == "completed":
            translated_path = status.get("output_path")
            if translated_path and os.path.exists(translated_path):
                print(f"Translation completed successfully.")
                
                # Copy to output path
                with open(translated_path, "rb") as src, open(output_path, "wb") as dst:
                    dst.write(src.read())
                
                print(f"Translated subtitle saved to: {output_path}")
                return 0
            break
        elif status["status"] == "error":
            print(f"Translation failed: {status.get('message', 'Unknown error')}")
            return 1
        
        print("Translating... Please wait.")
        time.sleep(3)
        wait_time += 3
    
    print("Timeout waiting for translation to complete. The operation may still be running in the background.")
    return 1

def transcribe_video(args):
    """Generate subtitles from video using speech-to-text"""
    print(f"Transcribing video: {args.input}")
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file does not exist: {args.input}")
        return 1
    
    if not is_valid_video_file(args.input):
        print(f"Error: Not a valid video file: {args.input}")
        return 1
    
    # Prepare output path
    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        # Set appropriate extension based on format
        if args.format == "ass":
            extension = "ass"
        elif args.format == "webvtt":
            extension = "vtt"
        else:
            extension = args.format
        output_path = f"{base_name}_transcribed.{extension}"
    else:
        # If output path is provided but has no extension, add the appropriate one
        _, ext = os.path.splitext(output_path)
        if not ext:
            if args.format == "ass":
                output_path = f"{output_path}.ass"
            elif args.format == "webvtt":
                output_path = f"{output_path}.vtt"
            else:
                output_path = f"{output_path}.{args.format}"
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Create required directories
    ensure_directory_exists("data/videos")
    ensure_directory_exists("data/processed")
    
    # Copy input to videos directory
    input_ext = os.path.splitext(args.input)[1]
    task_file_path = f"data/videos/{task_id}{input_ext}"
    
    if args.verbose:
        print(f"Copying input file to: {task_file_path}")
    
    with open(args.input, "rb") as src, open(task_file_path, "wb") as dst:
        dst.write(src.read())
    
    # Prepare options for transcription and formatting
    options = {
        "correct_grammar": args.grammar,
        "optimize_position": not args.no_position,
        "diarize_speakers": args.diarize,
        "max_speakers": args.max_speakers
    }
    
    # Add font style options for ASS format
    if args.format == "ass":
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
        options["font_style"] = font_style
    
    # Transcribe the video
    print(f"Transcribing video using {args.tool} tool with language: {args.language}...")
    processing_service.transcribe_video_to_subtitles(
        task_id=task_id, 
        language=args.language, 
        output_format=args.format,
        tool=args.tool,
        options=options
    )
    
    # Wait for completion
    import time
    max_wait = 300  # Maximum wait time in seconds (longer for transcription)
    wait_time = 0
    while wait_time < max_wait:
        status = subtitle_service.get_task_status(task_id)
        
        if args.verbose:
            print(f"Status: {status['status']}")
            if 'progress' in status:
                print(f"Progress: {status.get('progress', 0)}%")
            if 'step' in status:
                print(f"Step: {status.get('step', '')}")
        
        if status["status"] == "completed":
            output_file_path = status.get("output_path")
            if output_file_path and os.path.exists(output_file_path):
                print(f"Transcription completed successfully.")
                
                # Copy to output path
                with open(output_file_path, "rb") as src, open(output_path, "wb") as dst:
                    dst.write(src.read())
                
                print(f"Transcribed subtitle saved to: {output_path}")
                
                # Show warning if present
                if "warning" in status:
                    print(f"Warning: {status['warning']}")
                    
                return 0
            break
        elif status["status"] == "error":
            print(f"Transcription failed: {status.get('message', 'Unknown error')}")
            return 1
        
        # Print progress message
        progress = status.get("progress", 0)
        step = status.get("step", "processing")
        print(f"Transcribing... {progress}% ({step}). Please wait.")
        
        time.sleep(5)  # Longer sleep time for transcription
        wait_time += 5
    
    print("Timeout waiting for transcription to complete. The operation may still be running in the background.")
    return 1

def analyze_subtitle(args):
    """Analyze a subtitle file"""
    print(f"Analyzing subtitle file: {args.input}")
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file does not exist: {args.input}")
        return 1
    
    if not is_valid_subtitle_file(args.input):
        print(f"Error: Not a valid subtitle file: {args.input}")
        return 1
    
    # Prepare output path
    output_path = args.output
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Create required directories
    ensure_directory_exists("data/uploads")
    
    # Copy input to uploads directory
    input_ext = os.path.splitext(args.input)[1]
    task_file_path = f"data/uploads/{task_id}{input_ext}"
    
    if args.verbose:
        print(f"Copying input file to: {task_file_path}")
    
    with open(args.input, "rb") as src, open(task_file_path, "wb") as dst:
        dst.write(src.read())
    
    # Analyze the subtitle file
    print("Analyzing subtitle file...")
    analysis = processing_service.analyze_subtitle(task_id)
    
    if "error" not in analysis:
        # Print summary of analysis
        print("\nAnalysis Summary:")
        print(f"Total subtitles: {analysis['statistics'].get('total_subtitles', 0)}")
        print(f"Total characters: {analysis['statistics'].get('total_characters', 0)}")
        print(f"Average characters per subtitle: {analysis['statistics'].get('average_characters_per_subtitle', 0)}")
        print(f"File format: {analysis['statistics'].get('file_format', 'Unknown')}")
        
        if analysis.get('issues'):
            print("\nIssues Found:")
            for issue in analysis['issues']:
                severity = issue.get('severity', 'unknown').upper()
                issue_type = issue.get('type', 'unknown').replace('_', ' ').title()
                count = issue.get('count', 1)
                print(f"- [{severity}] {issue_type}: {count} instances")
        else:
            print("\nNo issues found.")
        
        if analysis.get('recommendations'):
            print("\nRecommendations:")
            for rec in analysis['recommendations']:
                print(f"- {rec.get('message', '')}")
        
        # Save to file if requested
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2)
            print(f"\nDetailed analysis saved to: {output_path}")
        
        return 0
    else:
        print("Analysis failed.")
        return 1

def main():
    """Main entry point for the CLI"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute the appropriate command
    if args.command == "process":
        return process_subtitle_file(args)
    elif args.command == "extract":
        return extract_subtitles(args)
    elif args.command == "transcribe":
        return transcribe_video(args)
    elif args.command == "translate":
        return translate_subtitle(args)
    elif args.command == "analyze":
        return analyze_subtitle(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
