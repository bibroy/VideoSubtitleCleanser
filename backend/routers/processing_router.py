from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query
from typing import Optional, List, Literal
from pydantic import BaseModel
from services import processing_service

router = APIRouter()

class ProcessingOptions(BaseModel):
    cleanse_errors: bool = True
    correct_grammar: bool = True
    remove_invalid_chars: bool = True
    correct_timing: bool = True
    optimize_position: bool = True
    target_language: Optional[str] = None
    diarize_speakers: bool = False
    enforce_font_consistency: bool = True
    remove_duplicate_lines: bool = True
    output_format: str = "vtt"

@router.post("/subtitle/{task_id}")
async def process_subtitle(
    task_id: str,
    background_tasks: BackgroundTasks,
    options: ProcessingOptions
):
    """
    Process a subtitle file with the specified options
    """
    # Schedule the processing task in the background
    background_tasks.add_task(
        processing_service.process_subtitle,
        task_id=task_id,
        options=options
    )
    
    return {
        "task_id": task_id,
        "status": "processing",
        "options": options.dict()
    }

@router.post("/extract/{task_id}")
async def extract_subtitles_from_video(
    task_id: str,
    background_tasks: BackgroundTasks,
    language: str = Form("eng")
):
    """
    Extract embedded subtitles from a video file
    """
    # Schedule the extraction task in the background
    background_tasks.add_task(
        processing_service.extract_subtitles,
        task_id=task_id,
        language=language
    )
    
    return {
        "task_id": task_id,
        "status": "extracting",
        "language": language
    }

@router.post("/transcribe/{task_id}")
async def transcribe_video_to_subtitles(
    task_id: str,
    background_tasks: BackgroundTasks,
    language: str = Form("en-US"),
    output_format: str = Form("webvtt"),
    tool: str = Form("auto")
):
    """
    Generate subtitles from video using speech-to-text technology
    
    Parameters:
    - task_id: Unique identifier for the task
    - language: Language code for transcription (default: en-US)
    - output_format: Output subtitle format (default: webvtt)
    - tool: Speech-to-text tool to use (default: auto)
      Options: "aws" (AWS Transcribe), "whisper" (OpenAI Whisper),
               "ffmpeg" (FFmpeg speech detection), or "auto" (try in order)
    """
    # Validate tool selection
    valid_tools = ["aws", "whisper", "ffmpeg", "auto"]
    if tool.lower() not in valid_tools:
        raise HTTPException(status_code=400, detail=f"Invalid tool selection. Must be one of: {', '.join(valid_tools)}")
    
    # Schedule the transcription task in the background
    background_tasks.add_task(
        processing_service.transcribe_video_to_subtitles,
        task_id=task_id,
        language=language,
        output_format=output_format,
        tool=tool.lower()
    )
    
    return {
        "task_id": task_id,
        "status": "transcribing",
        "language": language,
        "output_format": output_format,
        "tool": tool.lower()
    }

@router.post("/analyze/{task_id}")
async def analyze_subtitle(task_id: str):
    """
    Analyze a subtitle file and identify potential issues
    """
    analysis_result = processing_service.analyze_subtitle(task_id)
    
    return {
        "task_id": task_id,
        "analysis": analysis_result
    }

@router.post("/cancel/{task_id}")
async def cancel_processing(task_id: str):
    """
    Cancel an ongoing processing task
    """
    result = processing_service.cancel_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found or already completed")
    
    return {
        "task_id": task_id,
        "status": "cancelled"
    }
