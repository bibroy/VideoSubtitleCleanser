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
import tempfile
import uuid
import re
import json
import traceback
import time
import subprocess
from pathlib import Path
from datetime import timedelta

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import the dotenv loader to load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")

# Import backend config to ensure all paths and settings are initialized
# This will load AWS credentials from .env file through the dotenv loader in config.py
try:
    from backend.config import AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET
    print(f"Loaded AWS configuration from .env file via backend/config.py")
except ImportError:
    print("Error: Could not import AWS configuration from .env file via backend/config.py")
    print("Please ensure backend/config.py exists and .env file is properly configured.")
    sys.exit(1)
    
# Debug AWS configuration
    print(f"AWS Configuration in video_to_subtitle.py:")
    print(f"  - AWS Region: {AWS_REGION}")
    print(f"  - AWS Access Key: {'Set' if AWS_ACCESS_KEY else 'Not set'}")
    print(f"  - AWS Secret Key: {'Set' if AWS_SECRET_ACCESS_KEY else 'Not set'}")
    print(f"  - AWS S3 Bucket: {AWS_S3_BUCKET}")

# Import AWS utilities from the existing codebase
try:
    # First try to import from our enhanced AWS Transcribe utilities
    try:
        from backend.utils.aws_transcribe import (
            upload_to_s3, 
            start_transcription_job, 
            check_transcription_job_status,
            fetch_transcript,
            wait_for_transcription_job,
            CAN_USE_AWS,
            CAN_USE_TRANSCRIBE,
            CAN_USE_S3,
            CAN_USE_TRANSLATE,
            AWS_S3_BUCKET
        )
        print("Using enhanced AWS Transcribe utilities")
    except ImportError:
        # Fall back to original AWS utilities
        from backend.utils.aws_utils import (
            upload_to_s3, 
            start_transcription_job, 
            check_transcription_job_status,
            fetch_transcript,
            CAN_USE_AWS,
            CAN_USE_TRANSCRIBE,
            CAN_USE_S3,
            CAN_USE_TRANSLATE,
            AWS_S3_BUCKET
        )
        print("Using original AWS utilities")
        
    # Import error utilities
    from backend.utils.error_utils import log_error, try_import
    
    # Safe imports through the utility function
    boto3 = try_import('boto3')
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Warning: Could not import AWS utilities from backend.utils.aws_utils")
    print("AWS Transcribe functionality may be limited")
    # Fallback imports if backend utilities are not available
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    
    # AWS credentials are already imported from backend.config
    # Debug AWS configuration
    print(f"AWS Configuration in video_to_subtitle.py (fallback):")
    print(f"  - AWS Region: {AWS_REGION}")
    print(f"  - AWS Access Key: {'Set' if AWS_ACCESS_KEY else 'Not set'}")
    print(f"  - AWS Secret Key: {'Set' if AWS_SECRET_ACCESS_KEY else 'Not set'}")
    print(f"  - AWS S3 Bucket: {AWS_S3_BUCKET}")
    
    # Set AWS availability flags
    HAS_AWS_CREDENTIALS = bool(AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY)
    if not HAS_AWS_CREDENTIALS:
        print("\nWARNING: AWS credentials not found in environment variables.")
        print("To use AWS Transcribe, please set the following environment variables:")
        print("  - AWS_ACCESS_KEY: Your AWS access key")
        print("  - AWS_SECRET_ACCESS_KEY: Your AWS secret key")
        print("  - AWS_REGION: (Optional) AWS region (default: us-east-1)")
        print("  - AWS_S3_BUCKET: (Optional) S3 bucket name (default: videosubtitlecleanser-data-1)")
        print("\nYou can set these in a .env file in the project directory or in your system environment.")
        print("The script will fall back to Whisper if AWS credentials are not available.")

    # Check if boto3 is available
    if not boto3:
        print("\nWARNING: boto3 package not found but required for AWS services.")
        print("To use AWS Transcribe, please install boto3: pip install boto3")
        print("The script will fall back to Whisper if boto3 is not available.")

    CAN_USE_AWS = bool(boto3 and HAS_AWS_CREDENTIALS)
    CAN_USE_TRANSCRIBE = HAS_AWS_CREDENTIALS and boto3 is not None
    CAN_USE_S3 = HAS_AWS_CREDENTIALS and boto3 is not None
    CAN_USE_TRANSLATE = HAS_AWS_CREDENTIALS and boto3 is not None

    # Provide status of AWS configuration
    if CAN_USE_AWS:
        print(f"\nAWS configuration status:")
        print(f"  - AWS Credentials: {'Available' if HAS_AWS_CREDENTIALS else 'Missing'}")
        print(f"  - AWS Region: {AWS_REGION}")
        print(f"  - S3 Bucket: {AWS_S3_BUCKET}")
        print(f"  - boto3 Package: {'Available' if boto3 else 'Missing'}")
        print(f"  - Can use AWS services: {'Yes' if CAN_USE_AWS else 'No'}\n")
        
        # Configure boto3 session with credentials if available
        if HAS_AWS_CREDENTIALS:
            try:
                boto3.setup_default_session(
                    aws_access_key_id=AWS_ACCESS_KEY,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    region_name=AWS_REGION
                )
                print(f"AWS session configured with region: {AWS_REGION}")
                
                # Test AWS connectivity
                try:
                    s3 = boto3.client('s3')
                    s3.list_buckets()
                    print("AWS credentials verified successfully - S3 connection test passed")
                except Exception as e:
                    print(f"AWS credentials verification failed: {e}")
                    print("This may indicate invalid or expired credentials")
                    CAN_USE_AWS = False
                    CAN_USE_TRANSCRIBE = False
                    CAN_USE_S3 = False
            except Exception as e:
                print(f"Error setting up AWS session: {e}")
                CAN_USE_AWS = False
                CAN_USE_TRANSCRIBE = False
                CAN_USE_S3 = False
    
    # Define fallback implementations for AWS functions
    def upload_to_s3(file_path, object_name=None):
        print("Warning: AWS S3 not available. Using fallback implementation.")
        return {"success": False, "error": "AWS S3 not available"}
        
    def start_transcription_job(job_name, media_uri, settings=None, language_code="en-US"):
        """Fallback implementation of start_transcription_job with language_code parameter"""
        print("Warning: AWS Transcribe not available. Using fallback implementation.")
        return {"success": False, "error": "AWS Transcribe not available"}
        
    def check_transcription_job_status(job_name):
        print("Warning: AWS Transcribe not available. Using fallback implementation.")
        return {"success": False, "error": "AWS Transcribe not available"}
        
    def fetch_transcript(transcript_uri):
        print("Warning: AWS Transcribe not available. Using fallback implementation.")
        return {"success": False, "error": "AWS Transcribe not available"}

# Define global utility functions for AWS Transcribe
def wait_for_transcription_job(job_name, max_attempts=30, delay_seconds=10):
    """
    Wait for an AWS Transcribe job to complete with enhanced timeout handling and progress display
    
    Args:
        job_name: Name of the transcription job
        max_attempts: Maximum number of status check attempts (default: 30)
        delay_seconds: Delay between status checks in seconds (default: 10)
        
    Returns:
        Transcript URI if job completed successfully, None otherwise
    """
    import time
    
    # Get timeout from environment variable or CLI argument
    timeout_seconds = int(os.environ.get("AWS_TIMEOUT", os.environ.get("TIMEOUT", "300")))  # Default 5 minutes
    
    # Calculate max_attempts based on timeout and delay
    max_attempts = max(1, int(timeout_seconds / delay_seconds))
    
    print(f"Waiting for transcription job {job_name} to complete (timeout: {timeout_seconds}s)...")
    start_time = time.time()
    
    try:
        for attempt in range(max_attempts):
            # Check if we've exceeded the timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                print(f"\nTranscription job timed out after {int(elapsed)}s")
                return None
                
            # Check job status
            result = check_transcription_job_status(job_name)
            
            # Handle result based on format
            if isinstance(result, dict):
                # Backend utility format
                if result.get("success", False):
                    status = result.get("status")
                    if status == "COMPLETED":
                        print(f"\nTranscription job completed successfully after {int(elapsed)}s")
                        return result.get("transcript_uri")
                    elif status in ["FAILED", "ERROR"]:
                        print(f"\nTranscription job failed with status: {status}")
                        return None
            
            # Show progress indicator
            if attempt % 3 == 0:  # Update message every 3 attempts
                remaining = max(0, timeout_seconds - elapsed)
                print(f"\rJob status: IN_PROGRESS. {int(remaining)}s remaining...", end='', flush=True)
            
            # Display progress bar
            show_progress(attempt, max_attempts, message="AWS Transcribe")
            
            # Wait before next check
            time.sleep(delay_seconds)
        
        print(f"\nTranscription job timed out after {max_attempts} attempts")
        return None
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Transcription job may still be running in AWS.")
        print(f"You can check its status in the AWS console with job name: {job_name}")
        return None

# Global constants
AWS_TIMEOUT = 900  # 15 minutes timeout for AWS operations

# Import required modules
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Warning: Whisper module not found. Will use AWS Transcribe only.")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV (cv2) module not found. Video frame analysis will be limited.")

def check_whisper_availability(silent=False):
    """Check if Whisper is available and provide detailed installation instructions if not
    
    Args:
        silent (bool): If True, suppresses printing installation instructions
    
    Returns:
        bool: True if Whisper is available, False otherwise
    """
    if not WHISPER_AVAILABLE:
        if not silent:
            print("\nError: Whisper package not found but required for transcription.")
            print("\nTo install Whisper, please follow these steps:")
            print("1. Make sure you have Python 3.7-3.10 installed")
            print("2. Install FFmpeg if not already installed")
            print("3. Run the following commands:")
            print("   pip install torch torchvision torchaudio")
            print("   pip install openai-whisper")
            print("\nFor more details, visit: https://github.com/openai/whisper")
        return False
    return True

try:
    import pysrt
except ImportError:
    print("Error: pysrt module not found. Installing it with pip install pysrt")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pysrt"], check=True)
        import pysrt
    except:
        print("Error: Could not install pysrt. Please install it manually with: pip install pysrt")
        sys.exit(1)

def format_time_ass(seconds):
    """
    Format seconds as ASS timestamp (H:MM:SS.cc)
    """
    if isinstance(seconds, str):
        # If it's already a string, assume it's already formatted
        return seconds
        
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # ASS format uses centiseconds (1/100 of a second) instead of milliseconds
    centiseconds = int(td.microseconds / 10000)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

def apply_basic_grammar_corrections(text):
    """Apply basic grammar and punctuation corrections"""
    # Fix common spacing issues
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    text = re.sub(r'\s*([.,!?:;])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([.,!?:;])\s*', r'\1 ', text)  # Add space after punctuation
    
    # Fix common capitalization issues
    text = re.sub(r'^([a-z])', lambda m: m.group(1).upper(), text)  # Capitalize first letter
    
    # Fix common contractions
    text = re.sub(r'\bi m\b', "I'm", text, flags=re.IGNORECASE)
    text = re.sub(r'\bdont\b', "don't", text, flags=re.IGNORECASE)
    text = re.sub(r'\bcant\b', "can't", text, flags=re.IGNORECASE)
    text = re.sub(r'\bwont\b', "won't", text, flags=re.IGNORECASE)
    text = re.sub(r'\blets\b', "let's", text, flags=re.IGNORECASE)
    
    return text

def extract_audio_from_video(video_path, audio_path=None):
    """
    Extract audio from video file using ffmpeg with improved error handling
    """
    if not audio_path:
        # Create a temporary audio file
        audio_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.mp3")
    
    try:
        # Check if video file exists
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            return None
            
        # Use ffmpeg to extract audio with more robust settings
        # Use -hide_banner and -loglevel warning to reduce output noise
        # Use -stats to show progress
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-stats",
            "-y", "-i", video_path, 
            "-vn",  # No video
            "-acodec", "libmp3lame",  # Use libmp3lame codec for better compatibility
            "-ar", "16000",  # Audio sample rate
            "-ac", "1",  # Mono audio
            "-b:a", "128k",  # Audio bitrate
            audio_path
        ]
        
        print(f"Extracting audio with command: {' '.join(cmd)}")
        
        # Use a timeout to prevent hanging
        result = subprocess.run(
            cmd, 
            check=False,  # Don't raise exception, handle errors manually
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Check if the command was successful
        if result.returncode != 0:
            print(f"Error extracting audio. FFmpeg return code: {result.returncode}")
            print(f"FFmpeg stderr: {result.stderr}")
            
            # Try alternative approach with different codec
            print("Trying alternative FFmpeg settings...")
            alt_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "warning",
                "-y", "-i", video_path, 
                "-vn",
                "-acodec", "pcm_s16le",  # Use PCM codec instead
                "-ar", "16000",
                "-ac", "1",
                audio_path.replace(".mp3", ".wav")  # Use WAV format
            ]
            
            alt_result = subprocess.run(
                alt_cmd, 
                check=False,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if alt_result.returncode == 0:
                audio_path = audio_path.replace(".mp3", ".wav")
                print(f"Audio extracted using alternative method to: {audio_path}")
                return audio_path
            else:
                print(f"Alternative extraction also failed: {alt_result.stderr}")
                return None
        
        print(f"Audio successfully extracted to: {audio_path}")
        return audio_path
        
    except subprocess.TimeoutExpired:
        print("Error: FFmpeg process timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"Error extracting audio: {str(e)}")
        traceback.print_exc()
        return None

# Only define these functions if we couldn't import them from backend.utils.aws_utils
if 'upload_to_s3' not in globals():
    def upload_to_s3(file_path, bucket_name=None, object_name=None):
        """
        Upload a file to an S3 bucket
        """
        if bucket_name is None:
            bucket_name = AWS_S3_BUCKET
            
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        try:
            s3_client.upload_file(file_path, bucket_name, object_name)
            print(f"Uploaded {file_path} to s3://{bucket_name}/{object_name}")
            return f"s3://{bucket_name}/{object_name}"
        except (ClientError, NoCredentialsError) as e:
            print(f"Error uploading to S3: {e}")
            return None

# Only define these functions if we couldn't import them from backend.utils.aws_utils
if 'start_transcription_job' not in globals():
    def start_transcription_job(job_name, media_uri, settings=None, language_code="en-US"):
        """
        Start an AWS Transcribe job with speaker diarization
        """
        # Create Transcribe client
        transcribe = boto3.client('transcribe')
        
        try:
            # Handle target language if it's in settings
            target_language = None
            if settings and 'target_language' in settings:
                target_language = settings.pop('target_language')
            
            # Clean up settings to only include valid AWS Transcribe parameters
            aws_settings = {}
            if settings:
                # Only include valid AWS Transcribe settings parameters
                valid_settings = ['ShowSpeakerLabels', 'MaxSpeakerLabels', 'ChannelIdentification', 
                                 'ShowAlternatives', 'MaxAlternatives', 'VocabularyFilterName', 
                                 'VocabularyFilterMethod', 'VocabularyName']
                
                for key in valid_settings:
                    if key in settings:
                        aws_settings[key] = settings[key]
            
            # Start transcription job with appropriate language settings
            job_params = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': media_uri},
                'MediaFormat': 'mp3'
            }
            
            # Handle automatic language detection
            if language_code == 'auto':
                print("Using AWS Transcribe automatic language detection")
                job_params['IdentifyLanguage'] = True
            else:
                job_params['LanguageCode'] = language_code
            
            # Store the original language code for reference
            original_language_code = language_code
            
            # Only add Settings if we have valid settings
            if aws_settings:
                job_params['Settings'] = aws_settings
            
            # Add translation settings if target language is specified
            if target_language:
                # For AWS Transcribe, we need to use a separate API call for translation
                print(f"Target language {target_language} specified, but direct translation is not supported in this version.")
                print("Proceeding with transcription only. Translation will need to be handled separately.")
            
            # Print job parameters for debugging
            print(f"Starting AWS Transcribe job: {job_name}")
            print(f"Media URI: {media_uri}")
            print(f"Media Format: mp3")
            print(f"Language Code: {language_code}")
            print(f"Settings: {json.dumps(aws_settings, indent=2)}")
            
            response = transcribe.start_transcription_job(**job_params)
            
            return {"success": True, "job_name": job_name}
        except ClientError as e:
            print(f"AWS Transcribe error: {e}")
            return {"success": False, "error": str(e)}

# Only define these functions if we couldn't import them from backend.utils.aws_utils
if 'check_transcription_job_status' not in globals():
    def check_transcription_job_status(job_name):
        """
        Check status of an AWS Transcribe job
        """
        # Create Transcribe client
        transcribe = boto3.client('transcribe')
        
        try:
            # Get job status
            response = transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            print('mad: ', response)
            
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                print(f"Transcription job completed: {job_name}")
                transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                return {"success": True, "status": status, "transcript_uri": transcript_uri}
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown reason')
                print(f"Transcription job failed: {job_name}. Reason: {failure_reason}")
                return {"success": False, "status": status, "error": failure_reason}
            else:
                print(f"Transcription job status: {status}")
                return {"success": True, "status": status}
            
        except ClientError as e:
            print(f"Error checking transcription job status: {e}")
            return {"success": False, "error": str(e)}
            
    def wait_for_transcription_job(job_name, max_wait_seconds=900):
        """
        Wait for an AWS Transcribe job to complete with progress indicator
        """
        start_time = time.time()
        attempt = 0
        max_attempts = max_wait_seconds // 10  # Check every 10 seconds
        
        print(f"Waiting for AWS Transcribe job {job_name} to complete...")
        
        while time.time() - start_time < max_wait_seconds:
            try:
                attempt += 1
                
                # Show progress
                elapsed = int(time.time() - start_time)
                remaining = max(0, max_wait_seconds - elapsed)
                show_progress("AWS Transcribe", elapsed, max_wait_seconds, width=40)
                
                # Check job status
                status_result = check_transcription_job_status(job_name)
                
                if not status_result.get("success"):
                    print(f"\nError checking job status: {status_result.get('error')}")
                    return None
                
                status = status_result.get("status")
                
                if status == "COMPLETED":
                    print(f"\nTranscription job completed after {elapsed} seconds")
                    return status_result.get("transcript_uri")
                elif status == "FAILED":
                    print(f"\nTranscription job failed after {elapsed} seconds")
                    return None
                
                # Wait before checking again
                time.sleep(10)
            except Exception as e:
                print(f"\nError waiting for transcription job: {e}")
                return None
                
        # Timeout reached
        print(f"\nTranscription job timed out after {max_wait_seconds} seconds")
        return None

# Translation utility function
def translate_text(text, source_language_code, target_language_code):
    """
    Translate text using AWS Translate
    
    Args:
        text: Text to translate
        source_language_code: Source language code (e.g., en-US, fr-FR)
        target_language_code: Target language code (e.g., bn, hi)
        
    Returns:
        Translated text or original text if translation fails
    """
    # Convert language codes to format expected by AWS Translate
    # AWS Translate uses ISO language codes without country codes
    source_lang = source_language_code.split('-')[0]
    
    # Skip translation if source and target languages are the same
    if source_lang == target_language_code:
        print(f"Source and target languages are the same ({source_lang}). Skipping translation.")
        return text
        
    if not CAN_USE_TRANSLATE or not boto3:
        print("AWS Translate not available. Cannot perform translation.")
        return text
        
    try:
        # Create AWS Translate client
        translate = boto3.client('translate', region_name=AWS_REGION)
        
        # Perform translation
        response = translate.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_language_code
        )
        
        # Return translated text
        return response.get('TranslatedText', text)
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return text

# Function to translate subtitles in ASS format
def translate_ass_subtitles(ass_file_path, source_language_code, target_language_code):
    """
    Translate subtitles in an ASS file
    
    Args:
        ass_file_path: Path to the ASS subtitle file
        source_language_code: Source language code
        target_language_code: Target language code
        
    Returns:
        Path to the translated ASS file
    """
    if not os.path.exists(ass_file_path):
        print(f"Error: ASS file not found: {ass_file_path}")
        return None
        
    try:
        # Read the ASS file
        with open(ass_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Create output file path
        base_name, ext = os.path.splitext(ass_file_path)
        translated_file_path = f"{base_name}_{target_language_code}{ext}"
        
        # Track if we're in the Events section
        in_events = False
        translated_lines = []
        translation_count = 0
        total_lines = len(lines)
        
        print(f"\nTranslating subtitles from {source_language_code} to {target_language_code}...")
        
        for i, line in enumerate(lines):
            # Show progress every 10 lines
            if i % 10 == 0:
                show_progress(i, total_lines, message="Translation progress")
                
            # Check if we're entering the Events section
            if line.strip() == '[Events]':
                in_events = True
                translated_lines.append(line)
                continue
                
            # Check if we're in a new section
            if line.strip() and line.strip()[0] == '[' and line.strip()[-1] == ']':
                in_events = (line.strip() == '[Events]')
                translated_lines.append(line)
                continue
                
            # If we're in the Events section and the line starts with "Dialogue:"
            if in_events and line.strip().startswith('Dialogue:'):
                # Split the line by commas to separate the text
                parts = line.split(',', 9)  # Split into 10 parts, with the last part being the dialogue text
                
                if len(parts) >= 10:
                    # Extract the dialogue text
                    dialogue_text = parts[9].strip()

                    # Preserve double hyphens (--) for speaker diarization at the start
                    diar_marker = ""
                    spoken_text = dialogue_text
                    if dialogue_text.startswith("--"):
                        diar_marker = "--"
                        # Remove marker and any following whitespace
                        spoken_text = dialogue_text[2:].lstrip()
                    elif dialogue_text.startswith("{\\b1}--"):
                        # Handles bold speaker marker as used in some ASS stylings
                        diar_marker = "{\\b1}--"
                        spoken_text = dialogue_text[len(diar_marker):].lstrip()
                    # Add more patterns here if needed

                    # Translate only the spoken text
                    translated_spoken = translate_text(spoken_text, source_language_code, target_language_code)

                    # Re-attach diarization marker to translated text
                    translated_dialogue = f"{diar_marker} {translated_spoken}" if diar_marker else translated_spoken

                    # Replace the dialogue text with the translated text
                    parts[9] = translated_dialogue.strip()
                    
                    # Rejoin the parts and ensure newline
                    translated_line = ','.join(parts)
                    if not translated_line.endswith('\n'):
                        translated_line += '\n'
                    translated_lines.append(translated_line)
                    translation_count += 1
                else:
                    # If the line doesn't have enough parts, keep it as is
                    translated_lines.append(line)
            else:
                # Keep non-dialogue lines as they are, but ensure newline
                if not line.endswith('\n'):
                    line += '\n'
                translated_lines.append(line)
        
        # Show 100% progress
        show_progress(total_lines, total_lines, message="Translation progress")
        print(f"\nTranslated {translation_count} dialogue lines.")
        
        # Write the translated lines to a new file
        with open(translated_file_path, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)
            
        print(f"Translated subtitle file saved to: {translated_file_path}")
        return translated_file_path
    except Exception as e:
        print(f"Error translating subtitles: {str(e)}")
        traceback.print_exc()
        return None

# Only define these functions if we couldn't import them from backend.utils.aws_utils
if 'fetch_transcript' not in globals():
    def fetch_transcript(transcript_uri):
        """
        Fetch transcript data from URI
        """
        import urllib.request
        
        try:
            # Create a temporary file to store the transcript
            output_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.json")
            
            # Download the transcript file
            urllib.request.urlretrieve(transcript_uri, output_file)
            print(f"Downloaded transcript to: {output_file}")
            
            # Parse the JSON file
            with open(output_file, 'r') as f:
                transcript_data = json.load(f)
            
            # Clean up the temporary file
            os.remove(output_file)
            
            # Validate the transcript data
            if not transcript_data:
                print("Warning: Empty transcript data received from AWS Transcribe")
                return {"success": False, "error": "Empty transcript data", "data": None}
                
            # Check for expected structure
            if not isinstance(transcript_data, dict):
                print(f"Warning: Transcript data is not a dictionary, got {type(transcript_data)}")
                
            if isinstance(transcript_data, dict) and 'results' not in transcript_data:
                print(f"Warning: 'results' key not found in transcript data. Available keys: {list(transcript_data.keys())}")
                
            return {"success": True, "data": transcript_data}
        except Exception as e:
            print(f"Error downloading or parsing transcript: {e}")
            return {"success": False, "error": str(e)}
            
    def download_transcription_result(transcript_uri, output_file=None):
        """
        Download and parse the transcription result
        """
        if not output_file:
            output_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.json")
        
        try:
            # Use the fetch_transcript function if available
            result = fetch_transcript(transcript_uri)
            if result.get("success"):
                return result.get("data")
            else:
                # Fallback to direct download
                import urllib.request
                urllib.request.urlretrieve(transcript_uri, output_file)
                print(f"Downloaded transcript to: {output_file}")
                
                # Parse the JSON file
                with open(output_file, 'r') as f:
                    transcript_data = json.load(f)
                
                return transcript_data
        except Exception as e:
            print(f"Error downloading or parsing transcript: {e}")
            return None

def detect_text_in_video(video_path, subtitle_segments=None, sample_rate=5):
    """
    Use Amazon Rekognition to detect text in video frames and determine optimal subtitle positions
    
    Args:
        video_path: Path to the video file
        subtitle_segments: List of subtitle segments with timing information
        sample_rate: Number of frames to sample per subtitle (default: 5)
        
    Returns:
        Dictionary mapping timestamp ranges to optimal positions
    """
    # Check if AWS Rekognition is available
    if not CAN_USE_AWS or not boto3:
        print("AWS Rekognition not available. Using default subtitle positioning.")
        return {}
        
    # Check if OpenCV is available
    if not CV2_AVAILABLE:
        print("OpenCV not available. Using default subtitle positioning.")
        return {}
        
    try:
        # Get AWS Rekognition client
        rekognition = boto3.client(
            'rekognition',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        if not rekognition:
            print("Failed to create Rekognition client. Using default subtitle positioning.")
            return {}
            
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video. Using default subtitle positioning.")
            return {}
            
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"Video properties: {width}x{height}, {fps} fps, duration: {duration:.2f}s")
        
        # Determine which frames to sample
        sample_timestamps = []
        
        if subtitle_segments:
            # Sample frames at subtitle timestamps
            for segment in subtitle_segments:
                start_time = segment['start_time']
                end_time = segment['end_time']
                segment_duration = end_time - start_time
                
                # Sample multiple frames within each subtitle duration
                if segment_duration > 0:
                    num_samples = min(sample_rate, int(segment_duration * 2))
                    for i in range(num_samples):
                        sample_time = start_time + (segment_duration * i / num_samples)
                        sample_timestamps.append(sample_time)
        else:
            # If no subtitle segments provided, sample frames at regular intervals
            num_samples = min(30, int(duration / 5))  # Sample every 5 seconds, up to 30 samples
            for i in range(num_samples):
                sample_time = i * (duration / num_samples)
                sample_timestamps.append(sample_time)
        
        # Deduplicate and sort timestamps
        sample_timestamps = sorted(list(set(sample_timestamps)))
        print(f"Sampling {len(sample_timestamps)} frames for text detection")
        
        # Store detected text regions for each timestamp
        text_regions_by_time = {}
        
        # Process each sample timestamp
        for i, timestamp in enumerate(sample_timestamps):
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                continue
                
            # Show progress
            show_progress(i + 1, len(sample_timestamps), message="Analyzing video frames")
            
            # Save frame to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
                temp_path = temp_img.name
                cv2.imwrite(temp_path, frame)
            
            # Analyze frame with AWS Rekognition
            try:
                with open(temp_path, 'rb') as image_file:
                    image_bytes = image_file.read()
                    
                    # Detect text in the frame
                    response = rekognition.detect_text(Image={'Bytes': image_bytes})
                    detected_text = response.get('TextDetections', [])
                    
                    # Extract text regions (bounding boxes)
                    frame_text_regions = []
                    for text in detected_text:
                        if text.get('Type') == 'WORD' and text.get('Confidence', 0) > 70:
                            box = text.get('Geometry', {}).get('BoundingBox', {})
                            if box:
                                # Convert relative coordinates to absolute
                                x = int(box.get('Left', 0) * width)
                                y = int(box.get('Top', 0) * height)
                                w = int(box.get('Width', 0) * width)
                                h = int(box.get('Height', 0) * height)
                                
                                # Store detected text and its region
                                detected_word = text.get('DetectedText', '')
                                frame_text_regions.append({
                                    'text': detected_word,
                                    'box': (x, y, w, h),
                                    'confidence': text.get('Confidence', 0)
                                })
                    
                    # Store regions for this timestamp
                    if frame_text_regions:
                        text_regions_by_time[timestamp] = frame_text_regions
                        print(f"\nDetected {len(frame_text_regions)} text regions at {timestamp:.2f}s")
            except Exception as e:
                print(f"\nError analyzing frame at {timestamp:.2f}s: {e}")
            
            # Remove temporary file
            try:
                os.remove(temp_path)
            except Exception:
                pass
        
        # Release video capture
        cap.release()
        
        # Determine optimal subtitle positions based on detected text regions
        position_map = {}
        
        # Define screen regions (as fractions of screen height)
        top_region_height = 0.3  # Top 30% of screen
        bottom_region_height = 0.3  # Bottom 30% of screen
        
        top_region = (0, 0, width, int(height * top_region_height))
        bottom_region = (0, int(height * (1 - bottom_region_height)), width, int(height * bottom_region_height))
        
        # For each subtitle segment, determine optimal position
        if subtitle_segments:
            for segment in subtitle_segments:
                start_time = segment['start_time']
                end_time = segment['end_time']
                
                # Find text regions that overlap with this segment's time range
                overlapping_regions = []
                for ts, regions in text_regions_by_time.items():
                    if start_time <= ts <= end_time:
                        overlapping_regions.extend(regions)
                
                # Count text in each region
                top_text_count = 0
                bottom_text_count = 0
                
                for region in overlapping_regions:
                    x, y, w, h = region['box']
                    center_y = y + (h // 2)
                    
                    # Count text in top region
                    if center_y < height * top_region_height:
                        top_text_count += 1
                    # Count text in bottom region
                    elif center_y > height * (1 - bottom_region_height):
                        bottom_text_count += 1
                
                # Determine optimal position based on text density
                if top_text_count > 0 and bottom_text_count == 0:
                    # Text only at top, put subtitles at bottom
                    position = 'bottom_center'
                elif bottom_text_count > 0 and top_text_count == 0:
                    # Text only at bottom, put subtitles at top
                    position = 'top_center'
                elif top_text_count > 0 and bottom_text_count > 0:
                    # Text at both top and bottom, use raised bottom
                    position = 'raised_bottom'
                else:
                    # No text detected, default to bottom
                    position = 'bottom_center'
                
                # Store position for this segment
                position_map[(start_time, end_time)] = position
        
        print(f"\nDetermined optimal positions for {len(position_map)} subtitle segments")
        return position_map
    
    except Exception as e:
        print(f"Error in text detection: {e}")
        traceback.print_exc()
        return {}

def parse_aws_transcript_to_ass(transcript_data, output_ass, font_style=None, grammar=False, video_path=None):
    """
    Parse AWS Transcribe results and create an ASS subtitle file with speaker diarization
    
    Args:
        transcript_data: AWS Transcribe results in JSON format
        output_ass: Path to output ASS subtitle file
        font_style: Dictionary with font style parameters
        grammar: Whether to apply grammar correction
        video_path: Path to the video file for text detection and subtitle positioning
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print("Parsing AWS Transcribe results to ASS format...")
        
        # Enhanced validation of transcript data structure
        if not transcript_data:
            print("Error: Transcript data is empty or None")
            return False
            
        if not isinstance(transcript_data, dict):
            print(f"Error: Transcript data is not a dictionary, got {type(transcript_data)}")
            return False
            
        if 'results' not in transcript_data:
            print(f"Error: 'results' key not found in transcript data. Available keys: {list(transcript_data.keys())}")
            return False
            
        # Extract transcript items and speaker labels
        results = transcript_data['results']
        items = results.get('items', [])
        
        # Improved extraction of speaker labels
        speaker_labels_data = results.get('speaker_labels', {})
        speaker_segments = speaker_labels_data.get('segments', [])
        
        # Print detailed info about the transcript structure to help with debugging
        print(f"Transcript contains {len(items)} items")
        print(f"Speaker labels data contains {len(speaker_segments)} segments")
        
        # Set default font style if not provided
        if font_style is None:
            font_style = {}
        
        # Apply defaults for any missing style options
        font_name = font_style.get('font_name', 'Arial')
        font_size = font_style.get('font_size', 24)
        primary_color = font_style.get('primary_color', '&H00FFFFFF')  # White
        outline_color = font_style.get('outline_color', '&H00000000')  # Black
        back_color = font_style.get('back_color', '&H80000000')  # Semi-transparent black
        bold = font_style.get('bold', 0)
        italic = font_style.get('italic', 0)
        outline = font_style.get('outline', 2)
        shadow = font_style.get('shadow', 3)
        
        # Create a more intelligent segmentation approach
        print(f"Processing {len(items)} transcript items with {len(speaker_segments)} speaker segments")
        
        # Improved speaker mapping approach
        speaker_map = {}
        if speaker_segments:
            try:
                # Only print detailed structure information if needed for debugging
                # Commented out to reduce verbosity
                # if speaker_segments:
                #     print(f"Sample speaker segment structure: {json.dumps(speaker_segments[0], indent=2)[:200]}...")
                #     if speaker_segments[0].get('items') and len(speaker_segments[0].get('items', [])) > 0:
                #         print(f"Sample item structure: {json.dumps(speaker_segments[0]['items'][0], indent=2)}")
                
                # Build a comprehensive speaker map
                for segment in speaker_segments:
                    speaker_label = segment.get('speaker_label', 'spk_0')
                    segment_items = segment.get('items', [])
                    
                    for item in segment_items:
                        # Try different possible field names for item_id without verbose logging
                        item_id = None
                        for field in ['item_id', 'id', 'start_time']:
                            if field in item:
                                item_id = item[field]
                                break
                        
                        if item_id:
                            speaker_map[item_id] = speaker_label
                        # Only print warnings for missing identifiers if really needed
                        # else:
                        #     print(f"Warning: Could not find item identifier in: {item}")
                
                print(f"Created speaker map with {len(speaker_map)} entries")
                
                # Print only essential information about speaker mappings
                print(f"Created {len(speaker_map)} speaker mappings")
                
                # If no speaker mappings were created, print a warning
                if not speaker_map:
                    print("WARNING: No speaker mappings could be created. Speaker diarization will not work correctly.")
                    print("Please check the AWS Transcribe output format or enable debug mode for more details.")
            except Exception as e:
                print(f"Warning: Error mapping speaker labels: {e}")
                import traceback
                traceback.print_exc()
        
        # Get video path from options if available
        if video_path is None and isinstance(font_style, dict) and 'video_path' in font_style:
            video_path = font_style.get('video_path')
            
        # First pass: Group words into proper sentences with timing
        words = []
        current_sentence = {
            'start_time': None,
            'end_time': None,
            'speaker': None,
            'words': []
        }
        
        # Process all items to extract words with timing
        for i, item in enumerate(items):
            try:
                if item.get('type') == 'pronunciation':
                    # Extract word data
                    item_id = item.get('id', '')
                    if 'start_time' not in item or 'end_time' not in item:
                        continue
                    
                    start_time = float(item['start_time'])
                    end_time = float(item['end_time'])
                    
                    # Get content
                    alternatives = item.get('alternatives', [])
                    if not alternatives:
                        continue
                    content = alternatives[0].get('content', '')
                    if not content:
                        continue
                    
                    # Get speaker - try different possible item ID formats
                    speaker = None
                    for field in ['id', 'start_time']:
                        if field in item and item[field] in speaker_map:
                            speaker = speaker_map[item[field]]
                            break
                    
                    # If no match found, use the direct item_id
                    if speaker is None:
                        speaker = speaker_map.get(item_id, 'spk_0')
                    
                    # Add word to the list
                    words.append({
                        'content': content,
                        'start_time': start_time,
                        'end_time': end_time,
                        'speaker': speaker,
                        'item_id': item_id
                    })
                    
                elif item.get('type') == 'punctuation':
                    # Add punctuation to the last word
                    if words:
                        alternatives = item.get('alternatives', [])
                        if alternatives:
                            punct = alternatives[0].get('content', '')
                            if punct:
                                words[-1]['content'] += punct
            except Exception as e:
                print(f"Warning: Error processing item {i}: {e}")
                continue
        
        # Second pass: Group words into logical segments with proper timing
        segments = []
        if not words:
            print("Warning: No words found in transcript")
            return False
            
        # Constants for segmentation
        MAX_SEGMENT_LENGTH = 12  # Maximum words per segment
        MAX_SEGMENT_DURATION = 5.0  # Maximum segment duration in seconds
        PAUSE_THRESHOLD = 0.7  # Pause between words that suggests a natural break
        
        # Initialize the first segment
        current_segment = {
            'start_time': words[0]['start_time'],
            'end_time': words[0]['end_time'],
            'speaker': words[0]['speaker'],
            'text': [words[0]['content']],
            'speaker_changed': False
        }
        
        prev_speaker = words[0]['speaker']
        prev_end_time = words[0]['end_time']
        
        # Process remaining words
        for i in range(1, len(words)):
            word = words[i]
            speaker = word['speaker']
            content = word['content']
            start_time = word['start_time']
            end_time = word['end_time']
            
            # Check if we should start a new segment
            speaker_changed = speaker != prev_speaker
            time_gap = start_time - prev_end_time > PAUSE_THRESHOLD
            segment_too_long = len(current_segment['text']) >= MAX_SEGMENT_LENGTH
            segment_too_long_duration = end_time - current_segment['start_time'] > MAX_SEGMENT_DURATION
            
            # Removed verbose speaker change logging to reduce output
            # if speaker_changed:
            #     print(f"Speaker change detected: {prev_speaker} -> {speaker} at time {format_time_ass(start_time)}")
            
            if speaker_changed or time_gap or segment_too_long or segment_too_long_duration:
                # Finalize current segment
                segments.append(current_segment)
                
                # Start new segment
                current_segment = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'speaker': speaker,
                    'text': [content],
                    'speaker_changed': speaker_changed
                }
                
                # Reduced verbosity for speaker changes
                # if speaker_changed:
                #     print(f"Speaker change at {format_time_ass(start_time)}: {prev_speaker} -> {speaker}")
                #     print(f"  This segment will be marked with double hyphens: -- {content}")
            else:
                # Continue current segment
                current_segment['end_time'] = end_time
                current_segment['text'].append(content)
            
            prev_speaker = speaker
            prev_end_time = end_time
        
        # Add the last segment
        if current_segment['text']:
            segments.append(current_segment)
            
        print(f"Created {len(segments)} subtitle segments from transcript")
        
        # Merge very short segments if needed
        if len(segments) > 1:
            merged_segments = [segments[0]]
            for i in range(1, len(segments)):
                current = segments[i]
                previous = merged_segments[-1]
                
                # If segments are very short and from the same speaker, merge them
                # IMPORTANT: Don't merge segments with different speakers as we need to preserve speaker changes
                if (not current['speaker_changed'] and 
                    current['speaker'] == previous['speaker'] and
                    current['start_time'] - previous['end_time'] < 0.3 and
                    len(previous['text']) + len(current['text']) <= MAX_SEGMENT_LENGTH):
                    # Merge with previous segment
                    previous['end_time'] = current['end_time']
                    previous['text'].extend(current['text'])
                else:
                    # Add as a new segment
                    merged_segments.append(current)
            
            segments = merged_segments
            print(f"Merged to {len(segments)} final subtitle segments")
        
        # Ensure minimum duration for each segment
        MIN_DURATION = 1.0  # Minimum segment duration in seconds
        for segment in segments:
            if segment['end_time'] - segment['start_time'] < MIN_DURATION:
                segment['end_time'] = segment['start_time'] + MIN_DURATION
        
        # Apply grammar corrections if requested
        if grammar:
            for segment in segments:
                text = ' '.join(segment['text'])
                segment['text'] = [apply_basic_grammar_corrections(text)]
        
        # Detect text in video and determine optimal subtitle positions if video_path is provided
        position_map = {}
        if video_path and os.path.exists(video_path):
            print(f"Detecting text in video for optimal subtitle positioning: {video_path}")
            try:
                position_map = detect_text_in_video(video_path, segments)
                print(f"Detected text in {len(position_map)} time ranges")
            except Exception as e:
                print(f"Warning: Could not detect text in video: {e}")
        else:
            print("No video path provided or file does not exist, using default subtitle positions")
        
        # Create ASS file
            # Check if we're dealing with Bengali language
            is_bengali = False
            if language and (language.lower().startswith('bn') or target_language_code == 'bn'):
                is_bengali = True
                print("Bengali language detected, using Bengali-compatible font settings")
                
                # Use a Bengali-compatible font
                bengali_fonts = ['Nirmala UI', 'Vrinda', 'Shonar Bangla', 'Kalpurush', 'SolaimanLipi']
                font_name = bengali_fonts[0]
                print(f"Using Bengali-compatible font: {font_name}")
        
        with open(output_ass, 'w', encoding='utf-8') as f:
            # Write ASS header
            f.write("[Script Info]\n")
            f.write("Unicode: yes\n")
            f.write("; Script generated by VideoSubtitleCleanser using AWS Transcribe\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1280\n")
            f.write("PlayResY: 720\n")
            f.write("Timer: 100.0000\n")
            f.write("WrapStyle: 0\n")
            f.write("Unicode: yes\n")
            f.write("Collisions: Normal\n\n")
            
            # Write style definitions
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            
            # Set encoding value for Unicode support (1 = Default with Unicode support)
            encoding = 1
            # Secondary color (for karaoke effects, not typically used)
            # Define encoding (1 = UTF-8)
            encoding = 1  # Standard UTF-8 encoding for ASS files
            
            secondary_color = "&H000000FF"  # Blue
            
            # Default style (bottom center)
            default_style = f"Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,4,{outline},{shadow},2,10,10,10,{encoding}\n"
            f.write(default_style)
            
            # Top style (for subtitles that need to be at the top)
            top_style = f"Style: Top,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,4,{outline},{shadow},8,10,10,10,10,{encoding}\n\n"
            f.write(top_style)
            
            
            # Raised bottom style (for when there's text at the bottom)
            raised_bottom_style = f"Style: RaisedBottom,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,4,{outline},{shadow},2,10,10,70,{encoding}\n\n"
            f.write(raised_bottom_style)
            # Write events section
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            # Write subtitle entries
            for i, segment in enumerate(segments):
                # Format timestamps as ASS format (h:mm:ss.cc)
                start_time = format_time_ass(segment['start_time'])
                end_time = format_time_ass(segment['end_time'])
                
                # Get the text content
                text = ' '.join(segment['text'])
                
                # Apply speaker diarization with double hyphens only for speaker changes
                if segment.get('speaker_changed', False) and i > 0:
                    # Add double hyphens at the beginning for speaker changes
                    text = f"-- {text}"
                    # Removed verbose logging
                    # print(f"Added speaker change marker to segment {i+1}: {text}")
                    # speaker_label = segment.get('speaker', 'unknown')
                    # print(f"  Speaker changed to: {speaker_label}")
                
                # Default style is bottom
                style = "Default"
                
                # Check if we have position information for this time range
                if position_map:  # Only check if position_map is not empty
                    for time_range, position in position_map.items():
                        range_start, range_end = time_range
                        # Check if current segment overlaps with this time range
                        if not (segment['end_time'] < range_start or segment['start_time'] > range_end):
                            if position == 'top_center':
                                style = "Top"
                                break
                            elif position == 'raised_bottom':
                                style = "RaisedBottom"
                                break
                            elif position == 'bottom_center':
                                style = "Default"
                                break
                
                # Write ASS entry with the determined style
                f.write(f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}\n")
                
        print(f"ASS subtitle file created with AWS Transcribe results: {output_ass}")
        return True
    
    except Exception as e:
        print(f"Error parsing AWS transcript to ASS: {e}")
        traceback.print_exc()
        return False

def generate_ass_from_video(video_path, output_ass, language="en-US", diarize=True, grammar=False, font_style=None, use_aws=True, use_whisper=True, detect_text=True):
    """
    Generate ASS subtitles directly from video with all requested features
    Primary method: AWS Transcribe
    Fallback method: Whisper local transcription
    
    Args:
        video_path: Path to the input video file
        output_ass: Path to the output ASS subtitle file
        language: Language code for transcription
        diarize: Enable speaker diarization
        grammar: Apply grammar correction
        font_style: Dictionary with font style parameters
        use_aws: Try AWS Transcribe first
        use_whisper: Use Whisper as fallback or primary method
    """
    print(f"\nGenerating ASS subtitles directly from video: {video_path}")
    print(f"DEBUG: Language parameter received: '{language}' (type: {type(language).__name__})")
    
    # Handle auto language detection
    if language == 'auto':
        print("Using automatic language detection with AWS Transcribe")
    
    # Prepare output path
    if not output_ass:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_ass = f"{base_name}_subtitles.ass"
    
    # Try AWS Transcribe first if available and requested
    if use_aws:
        print("Attempting to use AWS Transcribe for high-quality transcription...")
        try:
            # Set a timeout for the entire AWS process
            aws_start_time = time.time()
            # AWS_TIMEOUT is now defined globally at the top of the file
            
            # Check if AWS Transcribe is available
            if not CAN_USE_TRANSCRIBE or not CAN_USE_S3:
                print("AWS Transcribe or S3 is not available. Falling back to Whisper.")
                raise Exception("AWS services not available")
                
            # Check if we've exceeded the timeout
            if time.time() - aws_start_time > AWS_TIMEOUT:
                print(f"AWS operations timed out after {AWS_TIMEOUT} seconds. Falling back to Whisper.")
                raise Exception("AWS timeout")
            
            # Step 1: Extract audio from video
            audio_path = extract_audio_from_video(video_path)
            if not audio_path:
                print("Failed to extract audio. Falling back to Whisper.")
                raise Exception("Audio extraction failed")
        
            # Step 2: Upload audio to S3 using the imported utility function
            try:
                # Generate a unique object name
                object_name = f"audio/{uuid.uuid4()}.mp3"
                
                # Upload to S3 using the utility function from backend.utils.aws_utils
                # This will use the properly configured AWS credentials
                upload_result = upload_to_s3(audio_path)
                
                if not upload_result.get("success", False) and not isinstance(upload_result, str):
                    print("Failed to upload audio to S3. Falling back to Whisper.")
                    raise Exception("S3 upload failed")
                    
                # Get the media URI
                audio_uri = upload_result.get("media_uri") if isinstance(upload_result, dict) else upload_result
            
                # Step 3: Start AWS Transcribe job
                job_name = f"transcribe-{uuid.uuid4()}"
                
                # Configure transcription settings
                settings = {}
                
                # Add speaker diarization settings if enabled
                if diarize:
                    settings["ShowSpeakerLabels"] = True
                    settings["MaxSpeakerLabels"] = 10  # Maximum number of speakers to identify
                    
                # Add other settings
                settings["ShowAlternatives"] = True
                settings["MaxAlternatives"] = 2
                
                # Start transcription job using the imported utility function
                print(f"DEBUG: Starting AWS Transcribe job with language: '{language}'")
                job_result = start_transcription_job(job_name, audio_uri, settings, language_code=language)
                
                # Check if job started successfully
                # Handle both dictionary format and simple string format for backward compatibility
                if isinstance(job_result, dict) and not job_result.get("success", False):
                    error_msg = job_result.get('error', 'Unknown error')
                    print(f"Failed to start AWS Transcribe job: {error_msg}")
                    print("Falling back to Whisper.")
                    raise Exception("Transcribe job failed to start")
                elif job_result is None:
                    print("Failed to start AWS Transcribe job: No result returned")
                    print("Falling back to Whisper.")
                    raise Exception("Transcribe job failed to start")
                
                # Step 4: Wait for transcription to complete
                print("Waiting for AWS Transcribe job to complete...")
                transcript_uri = wait_for_transcription_job(job_name)
                if not transcript_uri:
                    print("AWS Transcribe job failed or timed out. Falling back to Whisper.")
                    raise Exception("Transcribe job failed or timed out")
                
                # Step 5: Download and parse transcription results
                print(f"Downloading transcription results from: {transcript_uri}")
                transcript_result = fetch_transcript(transcript_uri)
                
                if not transcript_result.get("success", False):
                    print(f"Failed to download transcription results: {transcript_result.get('error', 'Unknown error')}")
                    print("Falling back to Whisper.")
                    raise Exception("Failed to download transcript")
                    
                transcript_data = transcript_result.get("data")
                
                # Validate transcript data
                if not transcript_data:
                    print("Error: Empty transcript data received from AWS Transcribe")
                    raise Exception("No transcript data available")
                    
                # Debug transcript data structure
                print(f"Transcript data keys: {list(transcript_data.keys()) if isinstance(transcript_data, dict) else 'Not a dictionary'}")
                if isinstance(transcript_data, dict) and 'results' in transcript_data:
                    results = transcript_data['results']
                    print(f"Results keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dictionary'}")
                
                # Step 6: Generate ASS file from transcription results
                # Pass video path for text detection if enabled
                if detect_text:
                    # Add video path to font_style dict for passing to parse_aws_transcript_to_ass
                    if font_style is None:
                        font_style = {}
                    font_style['video_path'] = video_path
                    
                success = parse_aws_transcript_to_ass(transcript_data, output_ass, font_style, grammar, video_path)
                
                # Clean up temporary files
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
                if success:
                    print(f"Successfully generated ASS subtitles using AWS Transcribe: {output_ass}")
                    return True
                else:
                    print("Failed to generate ASS file from AWS transcription. Falling back to Whisper.")
                    raise Exception("ASS generation failed")
                    
            except (ClientError, NoCredentialsError) as e:
                print(f"AWS service error: {e}. Falling back to Whisper.")
                raise
    
        except Exception as e:
            print(f"AWS Transcribe workflow failed: {e}")
            print("Falling back to local Whisper transcription...")
            
            # Fallback to Whisper
            return generate_ass_from_video_whisper(video_path, output_ass, language, diarize, grammar, font_style)

def generate_ass_from_video_whisper(video_path, output_ass, language="en-US", diarize=True, grammar=False, font_style=None):
    """
    Generate ASS subtitles directly from video using Whisper
    This is used as a fallback when AWS Transcribe is not available
    """
    print(f"\nGenerating ASS subtitles using Whisper: {video_path}")
    
    # Prepare output path
    if not output_ass:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_ass = f"{base_name}_subtitles.ass"
    
    try:
        # Step 1: Transcribe video directly using Whisper with a smaller model for speed
        print("Transcribing video with Whisper (tiny model for speed)...")
        
        # Use the tiny model for faster processing
        model = whisper.load_model("tiny")
        
        # Set a timeout for Whisper processing
        start_time = time.time()
        max_whisper_time = 60  # 60 seconds max for Whisper processing
        
        print("Loading Whisper model... this may take a moment")
        
        # Transcribe with word timestamps for better accuracy
        try:
            # Handle 'auto' language code for Whisper
            whisper_language = None  # Let Whisper auto-detect if language is 'auto'
            if language and language != 'auto':
                whisper_language = language[:2]  # Use first two chars of language code (e.g., 'en' from 'en-US')
            
            print(f"Using Whisper with language parameter: {whisper_language if whisper_language else 'auto-detect'}")
            
            result = model.transcribe(
                video_path, 
                language=whisper_language,  # None means Whisper will auto-detect
                word_timestamps=True,
                verbose=False,  # Reduce console output
                initial_prompt="This is a video with multiple speakers talking. Please transcribe accurately."
            )
            print("Whisper transcription completed successfully")
        except Exception as e:
            print(f"Error during Whisper transcription: {e}")
            traceback.print_exc()
            return False
        
        # Step 2: Generate ASS file directly from transcription result
        print("Generating ASS file directly from transcription...")
        
        # Set default font style if not provided
        if font_style is None:
            font_style = {}
        
        # Apply defaults for any missing style options
        font_name = font_style.get('font_name', 'Arial')
        font_size = font_style.get('font_size', 24)
        primary_color = font_style.get('primary_color', '&H00FFFFFF')  # White
        outline_color = font_style.get('outline_color', '&H00000000')  # Black
        back_color = font_style.get('back_color', '&H80000000')  # Semi-transparent black
        bold = font_style.get('bold', 0)
        italic = font_style.get('italic', 0)
        outline = font_style.get('outline', 2)
        shadow = font_style.get('shadow', 3)
        
        # Extract segments and preprocess them
        segments = result['segments']
        
        # Process segments for speaker diarization
        # We'll analyze the segments to identify likely speaker changes
        speaker_changes = [False] * len(segments)
        
        # Detect speaker changes based on content analysis
        # No special case handling for any specific video
        # Generic speaker change detection for all videos
        print("Using automatic speaker change detection")
        for i in range(1, len(segments)):  # Start from second segment
            prev_text = segments[i-1]['text'].strip()
            curr_text = segments[i]['text'].strip()
            
            # Check for dialogue patterns that indicate speaker changes
            sentence_end = any(prev_text.endswith(c) for c in ['.', '?', '!'])
            starts_with_dash = curr_text.startswith('-')
            starts_with_quote = curr_text.startswith('"') and not prev_text.endswith('"')
            starts_with_name = re.match(r'^[A-Z][a-z]+:', curr_text) is not None
            new_sentence = sentence_end and len(curr_text) > 0 and curr_text[0].isupper()
            
            # Determine if this is likely a new speaker
            speaker_changes[i] = any([starts_with_dash, starts_with_quote, starts_with_name, new_sentence])
            
            # Additional heuristic: alternating speakers in question-answer patterns
            if prev_text.endswith('?') and not curr_text.endswith('?'):
                speaker_changes[i] = True
        
        # Apply grammar corrections if requested
        if grammar:
            print("Applying grammar corrections...")
            for i in range(len(segments)):
                segments[i]['text'] = apply_basic_grammar_corrections(segments[i]['text'])
        
        # Create ASS file
        with open(output_ass, 'w', encoding='utf-8') as f:
            # Write ASS header
            f.write("[Script Info]\n")
            f.write("; Script generated by VideoSubtitleCleanser\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1280\n")
            f.write("PlayResY: 720\n")
            f.write("Timer: 100.0000\n")
            f.write("WrapStyle: 0\n\n")
            
            # Write style definitions
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            
            # Secondary color (for karaoke effects, not typically used)
            # Define encoding (1 = UTF-8)
            encoding = 1  # Standard UTF-8 encoding for ASS files
            
            secondary_color = "&H000000FF"  # Blue
            
            # Default style (bottom center)
            default_style = f"Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,4,{outline},{shadow},2,10,10,10,{encoding}\n"
            f.write(default_style)
            
            # Top style (for subtitles that need to be at the top)
            top_style = f"Style: Top,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,4,{outline},{shadow},8,10,10,10,{encoding}\n\n"
            f.write(top_style)
            
            
            # Raised bottom style (for when there's text at the bottom)
            raised_bottom_style = f"Style: RaisedBottom,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,4,{outline},{shadow},2,10,10,70,{encoding}\n\n"
            f.write(raised_bottom_style)
            # Write events section
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            # Write subtitle entries directly from the segments
            for i, segment in enumerate(segments):
                # Format timestamps as ASS format (h:mm:ss.cc)
                start_time = format_time_ass(segment['start'])
                end_time = format_time_ass(segment['end'])
                
                # Get the text content
                text = segment['text'].strip()
                
                # Apply speaker diarization if requested
                if diarize and i < len(speaker_changes) and speaker_changes[i]:
                    # Add two hyphens at the beginning for speaker change
                    text = f"-- {text.lstrip('-').strip()}"
                    print(f"Added speaker change marker to segment {i+1}: {text}")
                
                # Always use Default style for all subtitles
                style = "Default"
                
                # Write ASS entry
                f.write(f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}\n")
        
        print(f"ASS subtitle file created: {output_ass}")
        return True
        
    except Exception as e:
        print(f"Error generating ASS subtitles: {e}")
        traceback.print_exc()
        return False

def show_progress(current, total, width=50, message="Progress"):
    """
    Display an improved progress bar in the console with elapsed time
    
    Args:
        current: Current progress value
        total: Total progress value
        width: Width of the progress bar in characters
        message: Message to display before the progress bar
    """
    try:
        # Calculate progress
        progress = min(1.0, float(current) / max(1, float(total)))
        filled_width = int(width * progress)
        
        # Create progress bar with different characters for better visibility
        bar = '█' * filled_width + '▒' * (width - filled_width)
        percent = int(progress * 100)
        
        # Add spinner for visual feedback
        spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[current % 10]
        
        # Print progress bar
        print(f"\r{spinner} {message}: [{bar}] {percent}%", end='', flush=True)
        
        if current >= total:
            print("\r✓ Complete!" + " " * (width + 20))  # Clear the line
    except Exception:
        # Fallback to simple progress indicator if any error occurs
        print(f"\r{'.' * (current % 10)}", end='', flush=True)

def main():
    parser = argparse.ArgumentParser(
        description="Generate ASS subtitle files directly from video with all requested features",
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
    
    # Check if Whisper is available when needed
    if args.tool == "whisper" or args.tool == "auto":
        if not check_whisper_availability():
            return 1
        
    # Generate ASS subtitle file based on selected tool
    if args.tool == "whisper":
        print("Using Whisper transcription as requested...")
        # Use the Whisper implementation directly
        # Note: Whisper currently doesn't support direct translation, will use source language only
        success = generate_ass_from_video_whisper(
            args.input, 
            args.output, 
            args.source_language,  # Use source language for Whisper
            args.diarize,
            args.grammar,
            font_style,
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
    elif args.tool == "aws":
        print("Using AWS Transcribe as requested...")
        
        # Check AWS credentials and provide detailed feedback
        if not CAN_USE_TRANSCRIBE or not CAN_USE_S3 or not boto3:
            print("\nError: AWS Transcribe or S3 is not properly configured.")
            
            # Check for specific issues
            if not boto3:
                print("Error: boto3 library is not installed. Please install it with: pip install boto3")
            
            # Check AWS credentials - using values imported from backend.config
            # These are already loaded from .env file
            aws_key = AWS_ACCESS_KEY
            aws_secret = AWS_SECRET_ACCESS_KEY
            aws_region = AWS_REGION
            
            print("\nAWS Credentials Status:")
            print(f"  AWS_ACCESS_KEY: {'Set' if aws_key else 'NOT SET - Required'}")  
            print(f"  AWS_SECRET_ACCESS_KEY: {'Set' if aws_secret else 'NOT SET - Required'}")
            print(f"  AWS_REGION: {'Set' if aws_region else 'Not set - will use default'}")
            
            if not aws_key or not aws_secret:
                print("\nTo use AWS Transcribe, set these environment variables in your .env file:")
                print("  AWS_ACCESS_KEY=your_access_key")
                print("  AWS_SECRET_ACCESS_KEY=your_secret_key")
                print("  AWS_REGION=your_region (optional)")
                print("  AWS_S3_BUCKET=your_bucket (optional)")
                print("\nMake sure your .env file is in the project directory.")
                print("AWS credentials are only loaded from the .env file.")
            
            # Check if Whisper is available for fallback
            if not WHISPER_AVAILABLE:
                print("\nError: Cannot fall back to Whisper as it is not installed.")
                print("Please install Whisper using: pip install openai-whisper")
                return 1
                
            print("\nFalling back to Whisper...")
            return generate_ass_from_video_whisper(
                args.input, 
                args.output, 
                args.source_language, 
                args.diarize, 
                args.grammar, 
                font_style
            )
            
        # If we get here, AWS credentials are available
        try:
            print("Extracting audio from video...")
            audio_path = extract_audio_from_video(args.input)
            
            # Check if audio extraction was successful
            if not audio_path:
                print("Failed to extract audio from video.")
                
                # Check if Whisper is available for fallback
                if not WHISPER_AVAILABLE:
                    print("Error: Cannot fall back to Whisper as it is not installed.")
                    print("Please install Whisper using: pip install openai-whisper")
                    return 1
                    
                print("Falling back to Whisper...")
                return generate_ass_from_video_whisper(
                    args.input, 
                    args.output, 
                    args.source_language, 
                    args.diarize, 
                    args.grammar, 
                    font_style
                )
                
            # Upload to S3
            print("Uploading audio to S3...")
            upload_result = upload_to_s3(audio_path)
            
            # Check upload result
            if not upload_result or (isinstance(upload_result, dict) and not upload_result.get("success", False)):
                print("Failed to upload audio to S3.")
                
                # Check if Whisper is available for fallback
                if not WHISPER_AVAILABLE:
                    print("Error: Cannot fall back to Whisper as it is not installed.")
                    print("Please install Whisper using: pip install openai-whisper")
                    return 1
                    
                print("Falling back to Whisper...")
                return generate_ass_from_video_whisper(
                    args.input, 
                    args.output, 
                    args.source_language, 
                    args.diarize, 
                    args.grammar, 
                    font_style
                )
                
            # Get the media URI
            audio_uri = upload_result.get("media_uri") if isinstance(upload_result, dict) else upload_result
            
            # Start transcription job
            print("Starting AWS Transcribe job...")
            job_name = f"transcribe-{uuid.uuid4()}"
            
            # Configure transcription settings with speaker diarization only
            settings = {
                'ShowSpeakerLabels': args.diarize,
                'MaxSpeakerLabels': 10 if args.diarize else 0
            }
            
            # Log target language for information purposes, but don't add it to settings
            # as AWS Transcribe API doesn't support it and will reject the request
            if hasattr(args, 'target_language') and args.target_language:
                print(f"Note: Target language '{args.target_language}' specified, but AWS Transcribe API doesn't support direct translation.")
                print("Proceeding with transcription only in source language.")
                # Don't add target_language to settings as it would cause a parameter validation error
                
            # Language code is passed separately as a parameter
            language_code = args.source_language
            
            try:
                # Start the transcription job with language parameters passed correctly
                # Language code should be a separate parameter, not part of settings
                
                # Target language note already printed above
                
                # The imported start_transcription_job function uses AWS_TRANSCRIBE_LANGUAGE_CODE
                # from environment variables, so we need to set it temporarily
                original_lang_code = os.environ.get('AWS_TRANSCRIBE_LANGUAGE_CODE')
                os.environ['AWS_TRANSCRIBE_LANGUAGE_CODE'] = language_code
                
                print(f"DEBUG: CLI - Setting language_code for AWS Transcribe: '{language_code}'")
                
                try:
                    # Create a copy of settings to avoid modifying the original
                    job_settings = settings.copy() if settings else {}
                    
                    # Call the function with the correct parameters
                    print(f"DEBUG: CLI - Calling start_transcription_job with language_code: '{language_code}'")
                    job_response = start_transcription_job(
                        job_name=job_name,
                        media_uri=audio_uri,
                        settings=job_settings,
                        language_code=language_code  # Explicitly pass the language code
                    )
                finally:
                    # Restore the original environment variable
                    if original_lang_code:
                        os.environ['AWS_TRANSCRIBE_LANGUAGE_CODE'] = original_lang_code
                    else:
                        os.environ.pop('AWS_TRANSCRIBE_LANGUAGE_CODE', None)
                
                if not job_response or not job_response.get('success', False):
                    raise Exception("Failed to start transcription job")
                
                # Wait for the transcription job to complete
                print("Waiting for transcription to complete...")
                transcript_uri = wait_for_transcription_job(job_name, AWS_TIMEOUT)
                
                if not transcript_uri:
                    raise Exception("Transcription job failed or timed out")
                
                # Download and parse the transcript
                print("Downloading transcription results...")
                transcript_data = fetch_transcript(transcript_uri)
                
                if not transcript_data or not transcript_data.get('data'):
                    raise Exception("No transcript data available")
                
                # Parse the transcript to ASS format
                parse_aws_transcript_to_ass(
                    transcript_data.get('data'), 
                    args.output, 
                    font_style=font_style,
                    grammar=args.grammar,
                    video_path=args.input if args.detect_text else None
                )
                
                print(f"ASS subtitle file created: {args.output}")
                
                # Apply translation if needed
                if args.target_language:
                    print(f"\nApplying translation to {args.target_language}...")
                    translated_file = translate_ass_subtitles(
                        args.output,
                        args.source_language,
                        args.target_language
                    )
                    if translated_file:
                        print(f"Successfully created translated subtitle file: {translated_file}")
                
                return 0
                
            except Exception as e:
                print(f"Error in AWS Transcribe workflow: {e}")
                
                # Check if Whisper is available for fallback
                if not WHISPER_AVAILABLE:
                    print("Error: Cannot fall back to Whisper as it is not installed.")
                    print("Please install Whisper using: pip install openai-whisper")
                    return 1
                    
                print("Falling back to Whisper...")
                return generate_ass_from_video_whisper(
                    args.input, 
                    args.output, 
                    args.source_language, 
                    args.diarize, 
                    args.grammar, 
                    font_style
                )
                
        except Exception as e:
            print(f"Error in AWS workflow: {e}")
            
            # Check if Whisper is available for fallback
            if not WHISPER_AVAILABLE:
                print("Error: Cannot fall back to Whisper as it is not installed.")
                print("Please install Whisper using: pip install openai-whisper")
                return 1
                
            print("Falling back to Whisper...")
            return generate_ass_from_video_whisper(
                args.input, 
                args.output, 
                args.source_language, 
                args.diarize, 
                args.grammar, 
                font_style
            )
            
    else:  # auto - try AWS first, fallback to Whisper
        print("Using automatic tool selection (AWS with Whisper fallback)...")
        
        # First try AWS if available
        if CAN_USE_TRANSCRIBE and CAN_USE_S3 and boto3:
            print("Attempting to use AWS Transcribe...")
            try:
                # Try AWS Transcribe first
                return generate_ass_from_video(
                    args.input, 
                    args.output, 
                    args.source_language, 
                    args.diarize, 
                    args.grammar, 
                    font_style,
                    use_aws=True,
                    use_whisper=False  # Don't fall back to Whisper here, we'll handle it manually
                )
            except Exception as e:
                print(f"AWS Transcribe failed: {e}")
                # Continue to Whisper fallback below
        else:
            print("AWS Transcribe is not available or not properly configured.")
        
        # Check if Whisper is available for fallback
        if not WHISPER_AVAILABLE:
            print("Error: Cannot use Whisper as it is not installed.")
            print("Please install Whisper using: pip install openai-whisper")
            print("\nNeither AWS Transcribe nor Whisper is available. Cannot proceed.")
            return 1
        
        # Fall back to Whisper
        print("Using Whisper for transcription...")
        success = generate_ass_from_video_whisper(
            args.input, 
            args.output, 
            args.source_language, 
            args.diarize, 
            args.grammar, 
            font_style
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





