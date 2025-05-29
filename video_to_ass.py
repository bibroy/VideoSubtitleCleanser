#!/usr/bin/env python
"""
Generate ASS subtitle files directly from video with all requested features:
- Font style customization
- Proper grammar and spelling
- Multiple input/output language support
- Maintaining language sanctity
- Default subtitle position to bottom center
- Repositioning of subtitles to avoid overlay of text on video
- Speaker diarization with two hyphens at the beginning of dialogue for changed speakers
"""

import os
import sys
import argparse
import subprocess
import tempfile
import uuid
import re
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import from the existing project
from generate_ass_subtitles import convert_to_ass
from backend.utils.file_utils import ensure_directory_exists, is_valid_video_file

def transcribe_video_to_vtt(video_path, output_vtt, language="en-US", diarize=False, grammar=False):
    """
    Transcribe video to WebVTT format using the existing CLI functionality
    """
    # Create a temporary directory for intermediate files
    temp_dir = tempfile.mkdtemp()
    
    # Build the CLI command
    cmd = [
        "python", "cli.py", "transcribe",
        "--input", video_path,
        "--output", output_vtt,
        "--format", "webvtt",
        "--language", language
    ]
    
    # Add optional parameters
    if diarize:
        cmd.append("--diarize")
    
    # Run the transcription command
    print(f"Transcribing video: {video_path}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Transcription completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during transcription: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def process_vtt_for_diarization(vtt_path):
    """
    Process WebVTT file to ensure speaker changes are marked with two hyphens
    """
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace speaker markers with the double hyphen format
    # First, identify speaker changes
    lines = content.split('\n')
    processed_lines = []
    current_speaker = None
    
    for line in lines:
        # Skip WebVTT header and timing lines
        if line.startswith('WEBVTT') or '-->' in line or not line.strip():
            processed_lines.append(line)
            continue
            
        # Check for speaker markers like [Speaker 1]
        speaker_match = re.match(r'\[(.*?)\](.*)', line)
        if speaker_match:
            speaker, text = speaker_match.groups()
            if speaker != current_speaker:
                # New speaker - add double hyphen
                processed_lines.append(f"[{speaker}] -- {text.strip()}")
                current_speaker = speaker
            else:
                # Same speaker continues
                processed_lines.append(line)
        else:
            # No speaker marker
            processed_lines.append(line)
    
    # Write back the processed content
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(processed_lines))
    
    print(f"Processed VTT file with speaker diarization markers: {vtt_path}")
    return True

def correct_grammar(vtt_path):
    """
    Apply grammar and spelling corrections to the VTT file
    """
    # Use the CLI process command with grammar correction
    cmd = [
        "python", "cli.py", "process",
        "--input", vtt_path,
        "--output", vtt_path,
        "--grammar"
    ]
    
    print(f"Applying grammar corrections to: {vtt_path}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Grammar correction completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during grammar correction: {e}")
        return False

def generate_ass_from_video(video_path, output_ass=None, language="en-US", 
                           diarize=False, grammar=False, font_style=None):
    """
    Generate ASS subtitle file directly from video with all requested features
    """
    # Validate input file
    if not os.path.exists(video_path):
        print(f"Error: Input file does not exist: {video_path}")
        return False
    
    if not is_valid_video_file(video_path):
        print(f"Error: Not a valid video file: {video_path}")
        return False
    
    # Prepare output path
    if not output_ass:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_ass = f"{base_name}_subtitles.ass"
    
    # Create a temporary VTT file
    temp_vtt = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.vtt")
    
    try:
        # Step 1: Transcribe video to VTT
        if not transcribe_video_to_vtt(video_path, temp_vtt, language, diarize, grammar):
            print("Transcription failed. Aborting.")
            return False
        
        # Step 2: Process VTT for diarization if requested
        if diarize:
            process_vtt_for_diarization(temp_vtt)
        
        # Step 3: Apply grammar corrections if requested
        if grammar:
            correct_grammar(temp_vtt)
        
        # Step 4: Convert VTT to ASS with all the requested features
        convert_to_ass(temp_vtt, output_ass, optimize_positions=True, font_style=font_style)
        
        print(f"ASS subtitle file created: {output_ass}")
        return True
        
    except Exception as e:
        print(f"Error generating ASS subtitles: {e}")
        return False
    finally:
        # Clean up temporary files
        if os.path.exists(temp_vtt):
            os.remove(temp_vtt)

if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Generate ASS subtitle files directly from video with all requested features",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument("--input", required=True, help="Path to the input video file")
    parser.add_argument("--output", help="Path to the output ASS subtitle file")
    
    # Optional arguments
    parser.add_argument("--language", default="en-US", help="Language code for transcription (e.g., en-US, fr-FR)")
    parser.add_argument("--diarize", action="store_true", help="Enable speaker diarization")
    parser.add_argument("--grammar", action="store_true", help="Correct grammar and spelling")
    
    # Font style parameters
    parser.add_argument("--font-name", default="Arial", help="Font family name")
    parser.add_argument("--font-size", type=int, default=24, help="Font size in points")
    parser.add_argument("--primary-color", default="&H00FFFFFF", help="Text color in ASS format")
    parser.add_argument("--outline-color", default="&H00000000", help="Outline color in ASS format")
    parser.add_argument("--back-color", default="&H80000000", help="Background color in ASS format")
    parser.add_argument("--bold", type=int, choices=[0, 1], default=0, help="Bold text (0=off, 1=on)")
    parser.add_argument("--italic", type=int, choices=[0, 1], default=0, help="Italic text (0=off, 1=on)")
    parser.add_argument("--outline", type=int, default=2, help="Outline thickness")
    parser.add_argument("--shadow", type=int, default=3, help="Shadow depth")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Prepare font style dictionary
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
    
    # Generate ASS subtitle file
    success = generate_ass_from_video(
        args.input, 
        args.output, 
        args.language, 
        args.diarize, 
        args.grammar, 
        font_style
    )
    
    sys.exit(0 if success else 1)
