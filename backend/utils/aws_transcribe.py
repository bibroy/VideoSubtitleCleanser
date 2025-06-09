"""
AWS Transcribe utilities for VideoSubtitleCleanser
This module provides enhanced AWS Transcribe functionality with better error handling
"""

import os
import json
import time
import boto3
import traceback
from botocore.exceptions import ClientError, NoCredentialsError

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "videosubtitlecleanser-data")

# AWS Service availability flags
HAS_AWS_CREDENTIALS = bool(AWS_ACCESS_KEY and AWS_SECRET_ACCESS_KEY)
CAN_USE_AWS = bool(boto3 and HAS_AWS_CREDENTIALS)
CAN_USE_S3 = CAN_USE_AWS
CAN_USE_TRANSCRIBE = CAN_USE_AWS

def get_aws_client(service_name):
    """
    Get an AWS client for the specified service with proper error handling
    """
    if not CAN_USE_AWS:
        print(f"AWS {service_name} client not available: Missing credentials")
        return None
        
    try:
        return boto3.client(
            service_name,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    except Exception as e:
        print(f"Failed to create AWS {service_name} client: {e}")
        traceback.print_exc()
        return None

def upload_to_s3(file_path, s3_key=None):
    """
    Upload a file to S3 with enhanced error handling
    
    Args:
        file_path: Path to the file to upload
        s3_key: Key to use in S3 (defaults to filename)
        
    Returns:
        Dict with upload result info including media_uri if successful
    """
    if not CAN_USE_S3:
        return {"success": False, "error": "S3 upload not available"}
        
    try:
        # Create S3 client
        s3 = get_aws_client('s3')
        if not s3:
            return {"success": False, "error": "Failed to create S3 client"}
            
        # Generate S3 key if not provided
        if s3_key is None:
            s3_key = os.path.basename(file_path)
            
        # Upload to S3
        print(f"Uploading {file_path} to S3 bucket {AWS_S3_BUCKET} with key {s3_key}")
        s3.upload_file(file_path, AWS_S3_BUCKET, s3_key)
        media_uri = f"s3://{AWS_S3_BUCKET}/{s3_key}"
        
        return {
            "success": True,
            "media_uri": media_uri,
            "bucket": AWS_S3_BUCKET,
            "key": s3_key
        }
    except NoCredentialsError:
        return {"success": False, "error": "AWS credentials not found"}
    except ClientError as e:
        return {"success": False, "error": f"AWS S3 client error: {str(e)}"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": f"S3 upload error: {str(e)}"}

def start_transcription_job(job_name, media_uri, settings=None, language_code="en-US"):
    """
    Start an AWS Transcribe job with enhanced error handling
    
    Args:
        job_name: Name for the transcription job
        media_uri: URI of the media file (s3:// path)
        settings: Additional transcription settings
        language_code: Language code for transcription (e.g., en-US) or 'auto' for automatic detection
        
    Returns:
        Dict with job info
    """
    if not CAN_USE_TRANSCRIBE:
        return {"success": False, "error": "AWS Transcribe not available"}
        
    try:
        transcribe = get_aws_client('transcribe')
        if not transcribe:
            return {"success": False, "error": "Failed to create Transcribe client"}
            
        # Get file format from media_uri
        media_format = os.path.splitext(media_uri)[1].lower().lstrip('.')
        if media_format not in ['mp3', 'mp4', 'wav', 'flac', 'm4a']:
            media_format = 'mp3'  # Default format
            
        # Default settings for transcription    
        job_settings = {
            'ShowSpeakerLabels': True,
            'MaxSpeakerLabels': 10
        }
        
        # Update with custom settings if provided, but filter out invalid parameters
        if settings:
            # Only include valid AWS Transcribe settings parameters
            valid_settings_keys = [
                'ShowSpeakerLabels', 'MaxSpeakerLabels', 'ChannelIdentification',
                'ShowAlternatives', 'MaxAlternatives', 'VocabularyFilterName',
                'VocabularyFilterMethod', 'VocabularyName'
            ]
            
            # Filter settings to only include valid keys
            filtered_settings = {k: v for k, v in settings.items() if k in valid_settings_keys}
            job_settings.update(filtered_settings)
            
            # Handle target language if specified (for reference, not used in API call)
            if 'target_language' in settings:
                print(f"Note: Target language '{settings['target_language']}' specified, but AWS Transcribe API doesn't support direct translation.")
                print("Proceeding with transcription only in source language.")
            
        # Print job details for debugging
        print(f"Starting AWS Transcribe job: {job_name}")
        print(f"Media URI: {media_uri}")
        print(f"Media Format: {media_format}")
        print(f"Language Code: {language_code}")
        print(f"Settings: {json.dumps(job_settings, indent=2)}")
        
        # Check if any invalid parameters were in the original settings
        if settings:
            invalid_keys = [k for k in settings.keys() if k not in valid_settings_keys and k != 'target_language']
            if invalid_keys:
                print(f"Warning: Removed invalid settings parameters: {', '.join(invalid_keys)}")
        
        # Start transcription job with appropriate language settings
        try:
            if language_code == 'auto':
                print("Using AWS Transcribe automatic language detection")
                # For automatic language detection, we don't specify LanguageCode at all
                response = transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': media_uri},
                    MediaFormat=media_format,
                    IdentifyLanguage=True,
                    Settings=job_settings
                )
            else:
                # Use specified language code
                response = transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': media_uri},
                    MediaFormat=media_format,
                    LanguageCode=language_code,
                    Settings=job_settings
                )
        except ClientError as e:
            if 'Value \'auto\' at \'languageCode\'' in str(e):
                # Handle the specific error when 'auto' is rejected as a language code
                print("Retrying with IdentifyLanguage=True instead of language_code='auto'")
                response = transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': media_uri},
                    MediaFormat=media_format,
                    IdentifyLanguage=True,
                    Settings=job_settings
                )
            else:
                # Re-raise if it's a different error
                raise
        
        print(f"Transcription job started successfully: {job_name}")
        
        return {
            "success": True,
            "job_name": job_name,
            "status": response['TranscriptionJob']['TranscriptionJobStatus']
        }
    except ClientError as e:
        error_message = str(e)
        print(f"AWS Transcribe error: {error_message}")
        traceback.print_exc()
        return {"success": False, "error": error_message}
    except Exception as e:
        error_message = str(e)
        print(f"AWS Transcribe error: {error_message}")
        traceback.print_exc()
        return {"success": False, "error": error_message}

def check_transcription_job_status(job_name):
    """
    Check the status of an AWS Transcribe job
    
    Args:
        job_name: Name of the transcription job
        
    Returns:
        Dict with job status info
    """
    if not CAN_USE_TRANSCRIBE:
        return {"success": False, "error": "AWS Transcribe not available"}
        
    try:
        # Create Transcribe client
        transcribe = get_aws_client('transcribe')
        if not transcribe:
            return {"success": False, "error": "Failed to create Transcribe client"}
        
        # Get job status
        response = transcribe.get_transcription_job(
            TranscriptionJobName=job_name
        )
        
        status = response['TranscriptionJob']['TranscriptionJobStatus']
        
        if status == 'COMPLETED':
            transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            return {"success": True, "status": status, "transcript_uri": transcript_uri}
        elif status == 'FAILED':
            failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown reason')
            return {"success": False, "status": status, "error": failure_reason}
        else:
            return {"success": True, "status": status}
            
    except ClientError as e:
        return {"success": False, "error": f"AWS client error: {str(e)}"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": f"Error checking job status: {str(e)}"}

def fetch_transcript(transcript_uri):
    """
    Fetch and parse transcript from AWS Transcribe
    
    Args:
        transcript_uri: URI of the transcript file
        
    Returns:
        Dict with transcript data
    """
    if not CAN_USE_AWS:
        return {"success": False, "error": "AWS not available"}
        
    try:
        import requests
        
        # Download transcript
        response = requests.get(transcript_uri)
        if response.status_code != 200:
            return {"success": False, "error": f"Failed to download transcript: HTTP {response.status_code}"}
            
        # Parse transcript data
        transcript_data = response.json()
        
        return {"success": True, "data": transcript_data}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": f"Error fetching transcript: {str(e)}"}

def wait_for_transcription_job(job_name, max_wait_seconds=900, check_interval=10):
    """
    Wait for an AWS Transcribe job to complete with progress indicator
    
    Args:
        job_name: Name of the transcription job
        max_wait_seconds: Maximum time to wait in seconds
        check_interval: Time between status checks in seconds
        
    Returns:
        Transcript URI if job completed successfully, None otherwise
    """
    start_time = time.time()
    attempt = 0
    max_attempts = max_wait_seconds // check_interval
    
    print(f"Waiting for AWS Transcribe job {job_name} to complete...")
    
    while time.time() - start_time < max_wait_seconds:
        try:
            attempt += 1
            
            # Show progress
            elapsed = int(time.time() - start_time)
            remaining = max(0, max_wait_seconds - elapsed)
            percent = min(100, int(elapsed / max_wait_seconds * 100))
            
            # Check job status
            status_result = check_transcription_job_status(job_name)
            
            if not status_result.get("success"):
                print(f"\nError checking job status: {status_result.get('error')}")
                return None
            
            status = status_result.get("status")
            
            print(f"Job status: {status}. Elapsed: {elapsed}s, Remaining: {remaining}s ({percent}%)")
            
            if status == "COMPLETED":
                print(f"\nTranscription job completed after {elapsed} seconds")
                return status_result.get("transcript_uri")
            elif status == "FAILED":
                print(f"\nTranscription job failed after {elapsed} seconds")
                return None
            
            # Wait before checking again
            time.sleep(check_interval)
        except Exception as e:
            print(f"\nError waiting for transcription job: {e}")
            traceback.print_exc()
            return None
            
    # Timeout reached
    print(f"\nTranscription job timed out after {max_wait_seconds} seconds")
    return None
