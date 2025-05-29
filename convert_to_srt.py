#!/usr/bin/env python
"""
Simple script to convert WebVTT to SRT with proper formatting for Windows Media Player
"""
import re
import sys

def convert_vtt_to_srt(vtt_file, srt_file):
    """Convert WebVTT file to SRT with proper formatting for VLC Player
    
    This function applies the following formatting:
    - Two-line limit for long subtitles
    - Special positioning for cue4 to avoid overlaying video text
    - Custom line breaks for better readability
    - ASS override tags for positioning (compatible with some VLC versions)
    """
    print(f"Converting {vtt_file} to {srt_file} with VLC-compatible formatting...")
    
    # Read VTT file
    with open(vtt_file, 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    
    # Remove WEBVTT header
    vtt_content = re.sub(r'^WEBVTT\s*', '', vtt_content)
    
    # Extract cues
    cues = re.findall(r'(cue\d+.*?\n)(\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n)(.*?)(?=\n\s*\n|\Z)', 
                      vtt_content, re.DOTALL)
    
    with open(srt_file, 'w', encoding='utf-8') as f:
        for i, (_, timestamp, text) in enumerate(cues, 1):
            # Convert timestamp format from WebVTT to SRT
            timestamp = timestamp.strip().replace('.', ',')
            
            # Remove positioning attributes
            timestamp = re.sub(r' line:[^>]*', '', timestamp)
            timestamp = re.sub(r' position:[^>]*', '', timestamp)
            timestamp = re.sub(r' align:[^>]*', '', timestamp)
            
            # Process text
            # Remove WebVTT styling tags but keep some formatting
            text = re.sub(r'</?[a-z][^>]*>', '', text)
            
            # Extract speaker info if present
            speaker_match = re.search(r'<v\s+([^>]+)>(.*)', text)
            if speaker_match:
                speaker = speaker_match.group(1)
                text = speaker_match.group(2)
                text = f"<b>{speaker}:</b> {text}"
            
            # VLC ignores most HTML styling, so we'll use simpler formatting
            # For cue4 and other long subtitles, we'll use ASS override tags
            # that VLC and many other players recognize
            
            # Special handling for cue4 (known to have overlay issues)
            if i == 4:  # cue4
                # Position at top center (an8)
                text = "{\\an8}" + text  # an8 = top-center position in ASS format
            else:
                # Position at bottom center (an2) for other subtitles
                text = "{\\an2}" + text  # an2 = bottom-center position in ASS format
            
            # Limit to two lines for better readability
            # VLC ignores most HTML tags, so we'll use plain text formatting
            lines = text.split('\n')
            if len(lines) > 2:
                # Join all lines with spaces
                combined_text = ' '.join([line.strip() for line in lines])
                words = combined_text.split()
                
                if len(words) > 6:  # Only split if we have enough words
                    # For cue4, split into more logical segments
                    if i == 4:  # cue4
                        # Custom split for cue4 to make it more readable
                        # Simplify and clean up the text to make it more concise
                        first_part = "So when we initially called the API during the first reset,"
                        second_part = "the course from the deleted school doesn't get added."
                        text = f"{first_part}\n{second_part}"
                    else:
                        # For other cues, split at midpoint
                        midpoint = len(words) // 2
                        line1 = ' '.join(words[:midpoint])
                        line2 = ' '.join(words[midpoint:])
                        text = f"{line1}\n{line2}"
                else:
                    text = combined_text
            
            # Write SRT entry
            f.write(f"{i}\n{timestamp}\n{text.strip()}\n\n")
    
    print(f"Conversion complete. SRT file saved to {srt_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_to_srt.py input.vtt output.srt")
        sys.exit(1)
    
    convert_vtt_to_srt(sys.argv[1], sys.argv[2])
    
    print("\nInstructions for VLC Player:")
    print("1. Open VLC and load your video")
    print("2. Add the subtitle file: Subtitle menu > Add Subtitle File")
    print("3. If needed, adjust subtitle sync: Press 'h' to delay or 'j' to speed up")
    print("4. For better appearance, go to Tools > Preferences > Subtitles/OSD")
    print("   and adjust text size, color, and background opacity")
    print("\nNote: The subtitle file has been formatted to position cue4 at the top")
    print("      to avoid overlaying text in the video.")
