"""
AWS integration utilities for VideoSubtitleCleanser
This module provides safe wrappers for AWS service integrations with fallback options 
when AWS credentials are not available or when dependencies are missing
"""

import os
import json
import tempfile
from typing import Dict, Any, Optional, Callable
from functools import wraps
from pathlib import Path

# Import error utils
from backend.utils.error_utils import log_error, try_import, error_handler

# Safe imports
boto3 = try_import('boto3')
cv2 = try_import('cv2')
requests = try_import('requests')
language_tool_python = try_import('language_tool_python')

# Check for environment variables
from dotenv import load_dotenv
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "videosubtitlecleanser-data")
AWS_TRANSCRIBE_LANGUAGE_CODE = os.getenv("AWS_TRANSCRIBE_LANGUAGE_CODE", "en-US")

# AWS Service availability flags
HAS_AWS_CREDENTIALS = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
CAN_USE_AWS = bool(boto3 and HAS_AWS_CREDENTIALS)
CAN_USE_S3 = CAN_USE_AWS
CAN_USE_TRANSCRIBE = CAN_USE_AWS
CAN_USE_COMPREHEND = CAN_USE_AWS
CAN_USE_REKOGNITION = CAN_USE_AWS and bool(cv2)
CAN_USE_TRANSLATE = CAN_USE_AWS
CAN_USE_POLLY = CAN_USE_AWS

def requires_aws(service_name: str = None):
    """
    Decorator to check AWS availability before running a function
    Falls back to fallback_fn if AWS is not available
    
    Args:
        service_name: The AWS service name to check (transcribe, s3, comprehend, etc.)
                     If None, checks for general AWS availability
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Check if AWS is available
            if not CAN_USE_AWS:
                fallback_fn = kwargs.pop('fallback_fn', None)
                if fallback_fn:
                    return fallback_fn(*args, **kwargs)
                else:
                    raise RuntimeError(f"AWS not configured and no fallback function provided for {fn.__name__}")
                    
            # Check specific service
            if service_name:
                service_flag = globals().get(f"CAN_USE_{service_name.upper()}", False)
                if not service_flag:
                    fallback_fn = kwargs.pop('fallback_fn', None)
                    if fallback_fn:
                        return fallback_fn(*args, **kwargs)
                    else:
                        raise RuntimeError(f"AWS {service_name} not available and no fallback function provided")
                        
            # Service is available, run the function
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@error_handler
def get_aws_client(service_name: str) -> Any:
    """
    Safely get an AWS service client with proper error handling
    
    Args:
        service_name: Name of the AWS service (transcribe, s3, comprehend, etc.)
        
    Returns:
        AWS service client or None if not available
    """
    if not boto3 or not HAS_AWS_CREDENTIALS:
        return None
        
    try:
        return boto3.client(
            service_name,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    except Exception as e:
        log_error(e, f"Failed to create AWS {service_name} client")
        return None

@error_handler
def upload_to_s3(file_path: str, s3_key: str = None) -> Dict[str, Any]:
    """
    Upload a file to S3 with error handling
    
    Args:
        file_path: Path to the file to upload
        s3_key: Key to use in S3 (defaults to filename)
        
    Returns:
        Dict with upload result info including media_uri if successful
    """
    if not CAN_USE_S3:
        return {"error": True, "message": "S3 upload not available"}
        
    try:
        # Create S3 client
        s3 = get_aws_client('s3')
        if not s3:
            return {"error": True, "message": "Failed to create S3 client"}
            
        # Generate S3 key if not provided
        if s3_key is None:
            s3_key = os.path.basename(file_path)
            
        # Upload to S3
        s3.upload_file(file_path, AWS_S3_BUCKET, s3_key)
        media_uri = f"s3://{AWS_S3_BUCKET}/{s3_key}"
        
        return {
            "success": True,
            "media_uri": media_uri,
            "bucket": AWS_S3_BUCKET,
            "key": s3_key
        }
    except Exception as e:
        return log_error(e, "S3 upload error")

@error_handler
def delete_from_s3(s3_key: str) -> Dict[str, Any]:
    """
    Delete a file from S3 with error handling
    
    Args:
        s3_key: S3 key to delete
        
    Returns:
        Dict with deletion result
    """
    if not CAN_USE_S3:
        return {"error": True, "message": "S3 delete not available"}
        
    try:
        s3 = get_aws_client('s3')
        if not s3:
            return {"error": True, "message": "Failed to create S3 client"}
            
        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
        return {"success": True}
    except Exception as e:
        return log_error(e, "S3 delete error")

@error_handler
def start_transcription_job(job_name: str, media_uri: str, settings: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Start an AWS Transcribe job with error handling
    
    Args:
        job_name: Name for the transcription job
        media_uri: URI of the media file (s3:// path)
        settings: Additional transcription settings
        
    Returns:
        Dict with job info
    """
    if not CAN_USE_TRANSCRIBE:
        return {"error": True, "message": "AWS Transcribe not available"}
        
    try:
        transcribe = get_aws_client('transcribe')
        if not transcribe:
            return {"error": True, "message": "Failed to create Transcribe client"}
            
        # Get file format from media_uri
        media_format = os.path.splitext(media_uri)[1].lower().lstrip('.')
        if media_format not in ['mp3', 'mp4', 'wav', 'flac', 'm4a']:
            media_format = 'mp3'  # Default format
            
        # Default settings for transcription    
        job_settings = {
            'ShowSpeakerLabels': True,
            'MaxSpeakerLabels': 10
        }
        
        # Update with custom settings if provided
        if settings:
            job_settings.update(settings)
            
        # Start transcription job
        response = transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat=media_format,
            LanguageCode=AWS_TRANSCRIBE_LANGUAGE_CODE,
            Settings=job_settings
        )
        
        return {
            "success": True,
            "job_name": job_name,
            "status": response['TranscriptionJob']['TranscriptionJobStatus']
        }
    except Exception as e:
        return log_error(e, "AWS Transcribe error")

@error_handler
def check_transcription_job_status(job_name: str) -> Dict[str, Any]:
    """
    Check status of an AWS Transcribe job
    
    Args:
        job_name: Name of the transcription job
        
    Returns:
        Dict with job status info
    """
    if not CAN_USE_TRANSCRIBE:
        return {"error": True, "message": "AWS Transcribe not available"}
        
    try:
        transcribe = get_aws_client('transcribe')
        if not transcribe:
            return {"error": True, "message": "Failed to create Transcribe client"}
            
        response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        job_status = response['TranscriptionJob']['TranscriptionJobStatus']
        
        result = {
            "success": True,
            "job_name": job_name,
            "status": job_status
        }
        
        # Include transcript URI if job completed
        if job_status == 'COMPLETED':
            result['transcript_uri'] = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
        return result
    except Exception as e:
        return log_error(e, "AWS Transcribe status check error")

@error_handler
def fetch_transcript(transcript_uri: str) -> Dict[str, Any]:
    """
    Fetch transcript data from URI
    
    Args:
        transcript_uri: URI to the transcript JSON
        
    Returns:
        Dict with transcript data
    """
    if not requests:
        return {"error": True, "message": "Requests module not available"}
        
    try:
        response = requests.get(transcript_uri)
        return {
            "success": True,
            "data": response.json()
        }
    except Exception as e:
        return log_error(e, "Transcript fetch error")

@error_handler
def correct_text_with_comprehend(text: str) -> Dict[str, Any]:
    """
    Use AWS Comprehend to analyze and correct text
    
    Args:
        text: Text to analyze and correct
        
    Returns:
        Dict with corrected text and analysis info
    """
    if not CAN_USE_COMPREHEND:
        return {"error": True, "message": "AWS Comprehend not available"}
        
    try:
        comprehend = get_aws_client('comprehend')
        if not comprehend:
            return {"error": True, "message": "Failed to create Comprehend client"}
            
        # Analyze syntax
        syntax_response = comprehend.detect_syntax(
            Text=text,
            LanguageCode='en'
        )
        
        # In a full implementation, you would implement grammar correction logic based on the syntax analysis
        # For this demo, we'll just return the syntax info
        
        # Fallback to language_tool_python for actual corrections
        corrected_text = text
        if language_tool_python:
            try:
                language_tool = language_tool_python.LanguageTool('en-US')
                corrected_text = language_tool.correct(text)
                language_tool.close()
            except Exception as inner_e:
                corrected_text = text  # Use original text if correction fails
        
        return {
            "success": True,
            "original_text": text,
            "corrected_text": corrected_text,
            "syntax_analysis": syntax_response.get('SyntaxTokens', [])
        }
    except Exception as e:
        return log_error(e, "AWS Comprehend error")
