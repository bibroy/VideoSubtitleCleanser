"""
Timing service for VideoSubtitleCleanser
Handles subtitle timing synchronization and adjustment
"""

import os
import boto3
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import pysrt

from backend.config import (
    AWS_REGION, 
    AWS_ACCESS_KEY_ID, 
    AWS_SECRET_ACCESS_KEY,
    AWS_S3_BUCKET,
    AWS_TRANSCRIBE_LANGUAGE_CODE
)

def synchronize_subtitles(subs, video_path: str, use_aws: bool = True):
    """
    Improve subtitle timing synchronization with audio in the video
    Uses AWS Transcribe for word-level timing when available
    
    Args:
        subs: The subtitle objects to process
        video_path: Path to the video file
        use_aws: Whether to use AWS Transcribe for timing
    """
    if not boto3 or not use_aws or not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("AWS credentials not configured or AWS usage disabled. Using basic synchronization.")
        return _basic_timing_sync(subs, video_path)
    
    try:
        import uuid
        
        # Create a unique job name
        job_name = f"sync-{uuid.uuid4()}"
        
        # Extract audio using ffmpeg
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        audio_file.close()
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian format
            "-ar", "16000",  # 16 kHz sample rate (required by Transcribe)
            "-ac", "1",  # Mono
            audio_file.name
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Initialize AWS clients
        transcribe = boto3.client(
            'transcribe',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        s3 = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Upload to S3
        s3_key = f"{job_name}.wav"
        s3.upload_file(audio_file.name, AWS_S3_BUCKET, s3_key)
        media_uri = f"s3://{AWS_S3_BUCKET}/{s3_key}"
        
        # Start transcription job with word-level timestamps
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat='wav',
            LanguageCode=AWS_TRANSCRIBE_LANGUAGE_CODE,
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 10,
                'ShowAlternatives': False,
                'MaxAlternatives': 1
            }
        )
        
        # Wait for the transcription job to complete
        import time
        while True:
            status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            time.sleep(5)
        
        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            # Get the transcript with word-level timing
            transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            import requests
            transcript_response = requests.get(transcript_uri)
            transcript_data = transcript_response.json()
            
            # Clean up S3 object
            s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
            
            # Apply timing corrections
            return _apply_aws_timing_corrections(subs, transcript_data)
        else:
            print("AWS Transcribe job failed, using basic synchronization")
            return _basic_timing_sync(subs, video_path)
            
    except Exception as e:
        print(f"Error in AWS timing synchronization: {str(e)}")
        return _basic_timing_sync(subs, video_path)
    finally:
        # Clean up temporary audio file
        if os.path.exists(audio_file.name):
            os.remove(audio_file.name)

def _apply_aws_timing_corrections(subs, transcript_data):
    """
    Apply timing corrections from AWS Transcribe word-level timestamps
    """
    try:
        # Extract words with timestamps
        words = []
        if 'results' in transcript_data:
            items = transcript_data['results'].get('items', [])
            
            for item in items:
                if item.get('type') == 'pronunciation':
                    content = item.get('alternatives', [{}])[0].get('content', '')
                    start_time = float(item.get('start_time', 0))
                    end_time = float(item.get('end_time', 0))
                    
                    words.append({
                        'content': content,
                        'start_time': start_time,
                        'end_time': end_time
                    })
        
        if not words:
            print("No word timing data found in transcript")
            return subs
            
        # Adjust subtitle timing based on word matches
        from difflib import SequenceMatcher
        
        for sub in subs:
            sub_text = sub.text.lower()
            # Clean up the text for matching - remove speaker tags, punctuation
            import re
            cleaned_text = re.sub(r'\[.*?\]', '', sub_text)
            cleaned_text = re.sub(r'[.,!?;:"\'-]', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            
            # Create a sequence of words
            sub_words = cleaned_text.split()
            if not sub_words:
                continue
                
            # Try to find matching words in transcript
            matches = []
            for i, word_data in enumerate(words):
                if word_data['content'].lower() == sub_words[0].lower():
                    # Potential match for first word, check if subsequent words match
                    matching_length = 1
                    for j in range(1, min(len(sub_words), len(words) - i)):
                        if words[i + j]['content'].lower() == sub_words[j].lower():
                            matching_length += 1
                        else:
                            break
                    
                    if matching_length > 2 or (matching_length > 0 and matching_length == len(sub_words)):
                        # Found good match
                        start_time = word_data['start_time']
                        end_time = words[min(i + matching_length - 1, len(words) - 1)]['end_time']
                        matches.append((start_time, end_time, matching_length))
            
            if matches:
                # Find best match (highest number of matching words)
                best_match = max(matches, key=lambda x: x[2])
                start_time, end_time, _ = best_match
                
                # Adjust subtitle timing (convert to pysrt time object)
                import datetime
                
                # Keep some context before and after for readability
                start_padding = 0.1  # 100ms padding before
                end_padding = 0.3    # 300ms padding after
                
                start_ms = int((start_time - start_padding) * 1000)
                end_ms = int((end_time + end_padding) * 1000)
                
                if start_ms < 0:
                    start_ms = 0
                
                # Create new time objects
                sub.start = pysrt.SubRipTime(milliseconds=start_ms)
                sub.end = pysrt.SubRipTime(milliseconds=end_ms)
        
        return subs
    except Exception as e:
        print(f"Error applying AWS timing corrections: {str(e)}")
        return subs

def _basic_timing_sync(subs, video_path):
    """
    Basic subtitle timing adjustment
    Uses simple offset calculation based on audio analysis
    """
    try:
        import datetime
        from pydub import AudioSegment
        
        # Extract audio using pydub
        audio = AudioSegment.from_file(video_path)
        
        # Calculate audio loudness over time
        chunk_size = 100  # ms
        loudness = []
        
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            loudness.append(chunk.dBFS)
        
        # Detect significant audio events
        threshold = sum(loudness) / len(loudness) * 0.8  # 80% of average loudness
        audio_events = []
        
        for i, level in enumerate(loudness):
            if level > threshold:
                time_ms = i * chunk_size
                audio_events.append(time_ms)
        
        if not audio_events:
            return subs
        
        # Try to align subtitle timings with audio events
        for sub in subs:
            sub_start_ms = (sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds) * 1000 + sub.start.milliseconds
            
            # Find nearest audio event
            nearest_event = min(audio_events, key=lambda x: abs(x - sub_start_ms))
            
            # Only adjust if the difference is significant but not too large
            if 100 < abs(nearest_event - sub_start_ms) < 1000:
                # Apply adjustment
                offset = nearest_event - sub_start_ms
                sub.start.shift(milliseconds=offset)
                sub.end.shift(milliseconds=offset)
        
        return subs
        
    except Exception as e:
        print(f"Error in basic timing synchronization: {str(e)}")
        return subs
