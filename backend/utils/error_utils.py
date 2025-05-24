"""
Error handling utilities for VideoSubtitleCleanser
"""

import os
import logging
import traceback
from functools import wraps
from typing import Dict, Any, Callable, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("error_log.txt"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("subtitle_cleanser")

# Error classifications
ERROR_TYPES = {
    "AWS_ERROR": "AWS Service Error",
    "FILE_ERROR": "File Processing Error",
    "VIDEO_ERROR": "Video Processing Error",
    "AUDIO_ERROR": "Audio Processing Error",
    "SUBTITLE_ERROR": "Subtitle Processing Error",
    "IMPORT_ERROR": "Module Import Error",
    "CONFIG_ERROR": "Configuration Error",
    "UNKNOWN_ERROR": "Unknown Error"
}

def classify_error(error_instance: Exception) -> str:
    """
    Classify the type of error based on the exception
    """
    error_str = str(error_instance)
    error_class = error_instance.__class__.__name__
    
    if "boto" in error_class.lower() or "aws" in error_str.lower() or "s3" in error_str.lower():
        return "AWS_ERROR"
    elif "file" in error_str.lower() or "path" in error_str.lower() or "directory" in error_str.lower():
        return "FILE_ERROR"
    elif "video" in error_str.lower() or "ffmpeg" in error_str.lower() or "frame" in error_str.lower():
        return "VIDEO_ERROR"
    elif "audio" in error_str.lower() or "sound" in error_str.lower():
        return "AUDIO_ERROR" 
    elif "subtitle" in error_str.lower() or "srt" in error_str.lower() or "vtt" in error_str.lower():
        return "SUBTITLE_ERROR"
    elif "import" in error_str.lower() or "module" in error_str.lower() or "no module" in error_str.lower():
        return "IMPORT_ERROR"
    elif "config" in error_str.lower() or "setting" in error_str.lower() or "environment" in error_str.lower():
        return "CONFIG_ERROR"
    else:
        return "UNKNOWN_ERROR"

def log_error(error_instance: Exception, context: str = "", task_id: str = "") -> Dict[str, Any]:
    """
    Log an error and return a formatted error response
    
    Args:
        error_instance: The exception that occurred
        context: Additional context about where the error occurred
        task_id: ID of the task where the error occurred (if applicable)
        
    Returns:
        Dict with error info for API responses or UI display
    """
    # Get error details
    error_type = classify_error(error_instance)
    error_message = str(error_instance)
    error_traceback = traceback.format_exc()
    
    # Log the error
    logger.error(f"ERROR [{error_type}]: {error_message}")
    logger.debug(f"Context: {context}")
    logger.debug(f"Task ID: {task_id}")
    logger.debug(f"Traceback: {error_traceback}")
    
    # Format error response
    error_response = {
        "error": True,
        "error_type": ERROR_TYPES.get(error_type, "Error"),
        "message": error_message,
        "context": context
    }
    
    if task_id:
        error_response["task_id"] = task_id
        
    # For known errors, add suggestions
    error_response["suggestions"] = get_error_suggestions(error_type, error_message)
    
    return error_response

def get_error_suggestions(error_type: str, error_message: str) -> list:
    """
    Get suggestions for fixing common errors
    """
    suggestions = []
    
    if error_type == "AWS_ERROR":
        suggestions.extend([
            "Check your AWS credentials in .env file",
            "Ensure your AWS IAM user has the necessary permissions",
            "Verify that the AWS region is correctly configured"
        ])
        
        if "AccessDenied" in error_message:
            suggestions.append("Your AWS user doesn't have permission to access this resource")
        elif "NoSuchBucket" in error_message:
            suggestions.append("The specified S3 bucket doesn't exist")
        elif "ThrottlingException" in error_message:
            suggestions.append("AWS is throttling requests. Try again later.")
    
    elif error_type == "FILE_ERROR":
        suggestions.extend([
            "Check that the file exists and is accessible",
            "Verify the file path is correct",
            "Ensure you have read/write permissions for the file"
        ])
    
    elif error_type == "VIDEO_ERROR":
        suggestions.extend([
            "Verify the video file is not corrupted",
            "Check that ffmpeg is installed correctly",
            "Try with a different video format"
        ])
        
    elif error_type == "IMPORT_ERROR":
        suggestions.extend([
            "Make sure all required packages are installed",
            "Run 'pip install -r requirements.txt' to install dependencies",
            "Check for any conflicting package versions"
        ])
        
    elif error_type == "CONFIG_ERROR":
        suggestions.extend([
            "Ensure your .env file is properly set up",
            "Check that all required environment variables are defined",
            "Verify the configuration values are valid"
        ])
        
    return suggestions

def try_import(module_name: str) -> Optional[Any]:
    """
    Try to import a module, return None if not available
    """
    try:
        return __import__(module_name)
    except ImportError:
        logger.warning(f"Module {module_name} not available")
        return None

def error_handler(func):
    """
    Decorator for handling exceptions in functions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            task_id = kwargs.get('task_id', '')
            if not task_id and args and isinstance(args[0], str):
                task_id = args[0]
            
            context = f"Error in {func.__name__}"
            return log_error(e, context, task_id)
    
    return wrapper
