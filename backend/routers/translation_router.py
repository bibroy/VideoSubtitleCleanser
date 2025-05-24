from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from services import translation_service

router = APIRouter()

class TranslationRequest(BaseModel):
    task_id: str
    source_language: Optional[str] = None  # Auto-detect if not provided
    target_language: str
    preserve_formatting: bool = True
    quality: str = "standard"  # standard, premium

@router.post("/")
async def translate_subtitle(request: TranslationRequest):
    """
    Translate a subtitle file to the target language
    """
    try:
        result = translation_service.translate_subtitle(
            task_id=request.task_id,
            source_language=request.source_language,
            target_language=request.target_language,
            preserve_formatting=request.preserve_formatting,
            quality=request.quality
        )
        
        return {
            "task_id": request.task_id,
            "status": "translating",
            "target_language": request.target_language
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages")
async def get_supported_languages():
    """
    Get a list of supported languages for translation
    """
    return translation_service.get_supported_languages()

@router.get("/detect/{task_id}")
async def detect_language(task_id: str):
    """
    Detect the language of a subtitle file
    """
    language = translation_service.detect_language(task_id)
    
    return {
        "task_id": task_id,
        "detected_language": language
    }
