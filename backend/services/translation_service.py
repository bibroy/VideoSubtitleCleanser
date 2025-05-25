import os
import json
from typing import Dict, Any, List
from pathlib import Path
import pysrt

# Import error utilities
from backend.utils.error_utils import error_handler, log_error, try_import

# For AWS integrations - use safe imports
boto3 = try_import('boto3')

# To use AWS services in production, configure AWS credentials
# In this implementation, we'll simulate translation for demo purposes

# In-memory cache of language codes for demo purposes
LANGUAGE_CODES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de", 
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi"
}

def get_supported_languages() -> List[Dict[str, str]]:
    """
    Get a list of supported languages for translation
    """
    languages = []
    for name, code in LANGUAGE_CODES.items():
        languages.append({
            "name": name,
            "code": code
        })
    return languages

def detect_language(task_id: str) -> Dict[str, Any]:
    """
    Detect the language of a subtitle file
    In production, this would use AWS Comprehend or similar
    """
    from services.subtitle_service import get_subtitle_path
    
    subtitle_path = get_subtitle_path(task_id, original=True)
    if not subtitle_path:
        return {"error": "Subtitle file not found"}
    
    # Load subtitles
    try:
        subs = pysrt.open(subtitle_path, encoding='utf-8')
    except:
        try:
            subs = pysrt.open(subtitle_path, encoding='latin-1')
        except:
            return {"error": "Failed to parse subtitle file"}
    
    # Extract some text for language detection
    sample_text = ""
    for i, sub in enumerate(subs):
        sample_text += sub.text + " "
        if i > 10 or len(sample_text) > 500:
            break
    
    # In a real implementation, you would use AWS Comprehend or similar
    # For demo purposes, we'll simulate a detection result
    
    # Primitive detection based on character frequency
    # This is NOT a real language detection algorithm, just a demo
    char_counts = {}
    for c in sample_text.lower():
        if c.isalpha():
            char_counts[c] = char_counts.get(c, 0) + 1
    
    # Very simplistic checks
    if 'ñ' in char_counts and ('á' in char_counts or 'é' in char_counts):
        detected_code = "es"
        confidence = 0.85
    elif 'é' in char_counts and ('à' in char_counts or 'ç' in char_counts):
        detected_code = "fr"
        confidence = 0.82
    elif 'ä' in char_counts or 'ö' in char_counts or 'ü' in char_counts:
        detected_code = "de"
        confidence = 0.80
    else:
        # Default to English
        detected_code = "en"
        confidence = 0.70
    
    # Find language name from code
    detected_language = "Unknown"
    for name, code in LANGUAGE_CODES.items():
        if code == detected_code:
            detected_language = name
            break
    
    return {
        "code": detected_code,
        "language": detected_language,
        "confidence": confidence
    }

def translate_subtitle(
    task_id: str, 
    target_language: str, 
    source_language: str = None,
    preserve_formatting: bool = True,
    quality: str = "standard"
) -> Dict[str, Any]:
    """
    Translate a subtitle file to the target language
    In production, this would use AWS Translate or similar
    """
    from services.subtitle_service import get_subtitle_path, update_task_status
    
    update_task_status(task_id, "translating", {"progress": 0})
    
    # Get subtitle file path
    subtitle_path = get_subtitle_path(task_id, original=True)
    if not subtitle_path:
        update_task_status(task_id, "error", {"message": "Subtitle file not found"})
        return {"error": "Subtitle file not found"}
    
    # Load subtitles
    try:
        subs = pysrt.open(subtitle_path, encoding='utf-8')
    except:
        try:
            subs = pysrt.open(subtitle_path, encoding='latin-1')
        except:
            update_task_status(task_id, "error", {"message": "Failed to parse subtitle file"})
            return {"error": "Failed to parse subtitle file"}
    
    # Detect source language if not provided
    if not source_language:
        detected = detect_language(task_id)
        source_language = detected.get("code", "en")
    
    # Validate target language
    target_code = target_language
    if target_language in LANGUAGE_CODES.values():
        pass  # We already have the code
    elif target_language in LANGUAGE_CODES:
        target_code = LANGUAGE_CODES[target_language]
    else:
        update_task_status(task_id, "error", {"message": f"Unsupported target language: {target_language}"})
        return {"error": f"Unsupported target language: {target_language}"}
    
    # Translate the subtitles
    try:
        # In production, use AWS Translate or similar service
        # For demo purposes, we'll simulate translation
        
        # Simple translation function for demo (not a real translation)
        def simulate_translation(text, source, target):
            # This is NOT a real translation, just a demo
            if target == "es":
                text = text.replace("the", "el").replace("is", "es").replace("and", "y")
            elif target == "fr":
                text = text.replace("the", "le").replace("is", "est").replace("and", "et")
            elif target == "de":
                text = text.replace("the", "die").replace("is", "ist").replace("and", "und")
            return text

        for i, sub in enumerate(subs):
            # Preserve formatting by identifying formatting tags
            # This is a simplified approach - real implementation would be more robust
            
            if preserve_formatting:
                # Split by newlines and translate each line separately
                lines = sub.text.split('\n')
                translated_lines = []
                
                for line in lines:
                    # Translate the line
                    translated_line = simulate_translation(line, source_language, target_code)
                    translated_lines.append(translated_line)
                
                sub.text = '\n'.join(translated_lines)
            else:
                # Translate the whole text at once
                sub.text = simulate_translation(sub.text, source_language, target_code)
            
            # Update progress
            if i % 10 == 0:
                progress = min(99, int((i / len(subs)) * 100))
                update_task_status(task_id, "translating", {"progress": progress})
        
        # Save translated subtitles
        output_dir = Path("data/processed")
        output_dir.mkdir(exist_ok=True, parents=True)
        output_path = str(output_dir / f"{task_id}_translated.srt")
        
        subs.save(output_path, encoding='utf-8')
        
        update_task_status(task_id, "completed", {
            "progress": 100,
            "output_path": output_path,
            "source_language": source_language,
            "target_language": target_code,
            "download_url": f"/api/subtitles/download/{task_id}_translated"
        })
        
        return {
            "status": "completed",
            "output_path": output_path
        }
    
    except Exception as e:
        update_task_status(task_id, "error", {"message": str(e)})
        return {"error": str(e)}

def translate_subtitle_content(subs, target_language: str, source_language: str = None):
    """
    Translate subtitle content (used internally by processing service)
    Returns the translated subtitles object
    """
    # Validate target language
    target_code = target_language
    if target_language in LANGUAGE_CODES.values():
        pass  # We already have the code
    elif target_language in LANGUAGE_CODES:
        target_code = LANGUAGE_CODES[target_language]
    else:
        return subs  # Return original if language not supported
    
    # Simple translation function for demo (not a real translation)
    def simulate_translation(text, target):
        # This is NOT a real translation, just a demo
        if target == "es":
            text = text.replace("the", "el").replace("is", "es").replace("and", "y")
        elif target == "fr":
            text = text.replace("the", "le").replace("is", "est").replace("and", "et")
        elif target == "de":
            text = text.replace("the", "die").replace("is", "ist").replace("and", "und")
        return text
    
    # Translate each subtitle
    for sub in subs:
        # Split by newlines and translate each line separately
        lines = sub.text.split('\n')
        translated_lines = []
        
        for line in lines:
            # Translate the line
            translated_line = simulate_translation(line, target_code)
            translated_lines.append(translated_line)
        
        sub.text = '\n'.join(translated_lines)
    
    return subs
