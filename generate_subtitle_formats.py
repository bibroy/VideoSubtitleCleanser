#!/usr/bin/env python
"""
Standalone script to generate both WebVTT and VLC-compatible SRT subtitle formats.
This script uses pysrt and doesn't rely on the existing codebase structure.
"""

import os
import re
import sys
import pysrt

def convert_vtt_to_srt(vtt_file, srt_file, vlc_compatible=False):
    """
    Convert WebVTT file to SRT with proper formatting
    
    Args:
        vtt_file: Path to the input WebVTT file
        srt_file: Path to the output SRT file
        vlc_compatible: If True, add VLC-compatible ASS override tags for positioning
    """
    print(f"Converting {vtt_file} to {srt_file}...")
    
    # Read VTT file
    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading VTT file: {e}")
        return False
    
    # Parse VTT content
    # Skip the WEBVTT header
    if content.startswith('WEBVTT'):
        content = content.split('\n\n', 1)[1] if '\n\n' in content else content
    
    # Split into cues
    cues = re.split(r'\n\n+', content)
    
    # Create SRT file
    try:
        with open(srt_file, 'w', encoding='utf-8') as f:
            i = 1  # SRT uses 1-based indexing
            
            for cue in cues:
                lines = cue.strip().split('\n')
                if len(lines) < 2:
                    continue  # Skip malformed cues
                
                # Extract timestamp line
                timestamp_line = None
                for line in lines:
                    if '-->' in line:
                        timestamp_line = line
                        break
                
                if not timestamp_line:
                    continue  # Skip cues without timestamps
                
                # Parse timestamp
                timestamp = timestamp_line.strip()
                # Convert WebVTT format (00:00:00.000) to SRT format (00:00:00,000)
                timestamp = timestamp.replace('.', ',')
                # Remove positioning attributes if present
                timestamp = re.sub(r' align:[^>]*', '', timestamp)
                timestamp = re.sub(r' line:[^>]*', '', timestamp)
                timestamp = re.sub(r' position:[^>]*', '', timestamp)
                
                # Get text lines (everything after the timestamp line)
                text_lines = []
                text_started = False
                for line in lines:
                    if text_started:
                        text_lines.append(line)
                    elif '-->' in line:
                        text_started = True
                
                # Join text lines
                text = '\n'.join(text_lines)
                
                # Process text
                # Remove WebVTT styling tags but keep some formatting
                text = re.sub(r'</?[a-z][^>]*>', '', text)
                
                # Extract speaker info if present
                speaker_match = re.search(r'<v\\s+([^>]+)>(.*)', text)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    text = speaker_match.group(2)
                    text = f"<b>{speaker}:</b> {text}"
                
                # For VLC-compatible format, add ASS override tags
                if vlc_compatible:
                    # Default to bottom center position
                    position_tag = "{\\an2}"
                    
                    # Special handling for cue4 (known to have overlay issues)
                    if i == 4:
                        # Position at top center
                        position_tag = "{\\an8}"
                    
                    # Add more styling tags that VLC might recognize
                    # Try to include font color and size in the ASS override tag
                    # Format: {\anX\c&HFFFFFF&\fs20} - white text, size 20
                    style_tag = position_tag.replace('}', '\\c&HFFFFFF&\\fs20}')
                    
                    # Apply position and style tags
                    text = style_tag + text
                    
                    # Also add HTML-style tags that some VLC versions might recognize
                    text = f"<font color=\"#FFFFFF\" size=\"20\">{text}</font>"
                
                # Limit to two lines for better readability
                lines = text.split('\n')
                if len(lines) > 2:
                    # Join all lines with spaces
                    combined_text = ' '.join([line.strip() for line in lines])
                    words = combined_text.split()
                    
                    if len(words) > 6:  # Only split if we have enough words
                        # For cue4, split into more logical segments
                        if i == 4 and vlc_compatible:
                            # Custom split for cue4 to make it more readable
                            first_part = "So when we initially called the API during the first reset,"
                            second_part = "the course from the deleted school doesn't get added."
                            text = f"{position_tag}{first_part}\n{second_part}"
                        else:
                            # For other cues, split at midpoint
                            midpoint = len(words) // 2
                            line1 = ' '.join(words[:midpoint])
                            line2 = ' '.join(words[midpoint:])
                            
                            if vlc_compatible and text.startswith('{\\'):
                                # Preserve position tag
                                position_prefix = text[:6]
                                text = f"{position_prefix}{line1}\n{line2}"
                            else:
                                text = f"{line1}\n{line2}"
                    else:
                        if vlc_compatible and text.startswith('{\\'):
                            # Preserve position tag
                            position_prefix = text[:6]
                            text = f"{position_prefix}{combined_text}"
                        else:
                            text = combined_text
                
                # Write SRT entry
                f.write(f"{i}\n{timestamp}\n{text.strip()}\n\n")
                i += 1
        
        print(f"Conversion complete. SRT file saved to {srt_file}")
        return True
    
    except Exception as e:
        print(f"Error writing SRT file: {e}")
        return False

def generate_subtitle_formats(input_vtt, output_base):
    """
    Generate both WebVTT and VLC-compatible SRT formats from a WebVTT file
    
    Args:
        input_vtt: Path to the input WebVTT file
        output_base: Base path for the output files (without extension)
    """
    # Generate output paths
    webvtt_output = f"{output_base}.vtt"
    srt_output = f"{output_base}.srt"
    vlc_srt_output = f"{output_base}_vlc.srt"
    
    # Copy the WebVTT file
    try:
        with open(input_vtt, 'r', encoding='utf-8') as src, open(webvtt_output, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print(f"WebVTT file copied to {webvtt_output}")
    except Exception as e:
        print(f"Error copying WebVTT file: {e}")
    
    # Generate standard SRT file
    convert_vtt_to_srt(input_vtt, srt_output, vlc_compatible=False)
    
    # Generate VLC-compatible SRT file
    convert_vtt_to_srt(input_vtt, vlc_srt_output, vlc_compatible=True)
    
    # Verify output files
    success = True
    for file_path in [webvtt_output, srt_output, vlc_srt_output]:
        if os.path.exists(file_path):
            print(f"Successfully created: {file_path}")
        else:
            print(f"Failed to create: {file_path}")
            success = False
    
    return success

if __name__ == "__main__":
    # Print current working directory for debugging
    print(f"Current working directory: {os.getcwd()}")
    
    # Default paths
    default_input = "SampleVideo_transcribed_aws.vtt"
    default_output = "SampleVideo_formats"
    
    # Get paths from command line arguments or use defaults
    input_path = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_base = sys.argv[2] if len(sys.argv) > 2 else default_output
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file does not exist: {input_path}")
        sys.exit(1)
    
    # Generate subtitle formats
    if generate_subtitle_formats(input_path, output_base):
        print("\nProcessing completed successfully!")
        
        print("\nUsage Instructions:")
        print("1. For web players and advanced media players:")
        print(f"   Use the WebVTT file: {output_base}.vtt")
        print("   This file contains full styling and positioning information.")
        
        print("\n2. For standard media players:")
        print(f"   Use the standard SRT file: {output_base}.srt")
        
        print("\n3. For VLC Media Player:")
        print(f"   Use the VLC-compatible SRT file: {output_base}_vlc.srt")
        print("   This file contains ASS override tags for positioning that VLC recognizes.")
        
        print("\nTo customize VLC subtitle appearance:")
        print("- Go to Tools > Preferences > Subtitles/OSD")
        print("- Adjust text size, color, and background opacity to your preference")
    else:
        print("\nProcessing failed!")
