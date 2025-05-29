#!/usr/bin/env python
"""
Test script to demonstrate the enhanced subtitle processing with both WebVTT and VLC-compatible SRT formats.
This script directly uses the processing_service functions to generate both formats.
"""

import os
import sys
from pathlib import Path
import pysrt

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the processing service
from backend.services.processing_service import load_subtitles, save_subtitles, optimize_subtitle_position

def test_subtitle_formats(input_vtt, output_base, video_path=None):
    """
    Process a WebVTT subtitle file and generate both WebVTT and VLC-compatible SRT formats.
    
    Args:
        input_vtt: Path to the input WebVTT file
        output_base: Base path for the output files (without extension)
        video_path: Optional path to the video file for position optimization
    """
    print(f"Processing subtitle file: {input_vtt}")
    
    # Ensure the input file exists
    if not os.path.exists(input_vtt):
        print(f"Error: Input file does not exist: {input_vtt}")
        return False
    
    # Load the subtitles
    subs = load_subtitles(input_vtt)
    if not subs:
        print(f"Error: Failed to load subtitles from: {input_vtt}")
        return False
    
    print(f"Loaded {len(subs)} subtitle entries")
    
    # Optimize subtitle positions if video is provided
    if video_path and os.path.exists(video_path):
        print(f"Optimizing subtitle positions using video: {video_path}")
        subs = optimize_subtitle_position(subs, video_path)
    
    # Save in both formats
    print("Generating both WebVTT and VLC-compatible SRT formats...")
    save_subtitles(subs, output_base, format="both")
    
    # Verify the output files
    vtt_path = f"{output_base}.vtt"
    srt_path = f"{output_base}_vlc.srt"
    
    if os.path.exists(vtt_path):
        print(f"WebVTT file created: {vtt_path}")
    else:
        print(f"Error: WebVTT file was not created: {vtt_path}")
    
    if os.path.exists(srt_path):
        print(f"VLC-compatible SRT file created: {srt_path}")
    else:
        print(f"Error: VLC-compatible SRT file was not created: {srt_path}")
    
    return True

if __name__ == "__main__":
    # Enable more verbose output for debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Print current working directory
    print(f"Current working directory: {os.getcwd()}")
    
    # Default paths
    default_input = "SampleVideo_transcribed_aws.vtt"
    default_output = "SampleVideo_dual_format"
    default_video = "SampleVideo.mp4"
    
    # Get paths from command line arguments or use defaults
    input_path = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_path = sys.argv[2] if len(sys.argv) > 2 else default_output
    video_path = sys.argv[3] if len(sys.argv) > 3 else default_video
    
    # Check if input files exist
    print(f"Checking if input file exists: {input_path}")
    print(f"File exists: {os.path.exists(input_path)}")
    
    if os.path.exists(video_path):
        print(f"Video file exists: {video_path}")
    else:
        print(f"Video file does not exist: {video_path}")
        video_path = None
    
    # Run the test
    if test_subtitle_formats(input_path, output_path, video_path):
        print("\nProcessing completed successfully!")
        
        print("\nUsage Instructions:")
        print("1. For web players and advanced media players:")
        print(f"   Use the WebVTT file: {output_path}.vtt")
        print("   This file contains full styling and positioning information.")
        
        print("\n2. For VLC Media Player:")
        print(f"   Use the SRT file: {output_path}_vlc.srt")
        print("   This file contains ASS override tags for positioning that VLC recognizes.")
        
        print("\nTo customize VLC subtitle appearance:")
        print("- Go to Tools > Preferences > Subtitles/OSD")
        print("- Adjust text size, color, and background opacity to your preference")
    else:
        print("\nProcessing failed!")
