from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import uuid
from datetime import datetime
from services import subtitle_service

router = APIRouter()

@router.post("/upload")
async def upload_subtitle_file(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(None)
):
    """
    Upload a subtitle file for processing
    """
    if not task_id:
        task_id = str(uuid.uuid4())
    
    # Validate file type
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.srt', '.vtt', '.sub', '.sbv', '.smi', '.ssa', '.ass']:
        raise HTTPException(status_code=400, detail="Unsupported subtitle format")
    
    # Save the file
    file_path = f"data/uploads/{task_id}{file_extension}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {
        "task_id": task_id,
        "filename": file.filename,
        "upload_time": datetime.now().isoformat(),
        "status": "uploaded"
    }

@router.post("/upload_video")
async def upload_video_file(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(None)
):
    """
    Upload a video file for subtitle extraction or processing
    """
    if not task_id:
        task_id = str(uuid.uuid4())
    
    # Validate file type
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']:
        raise HTTPException(status_code=400, detail="Unsupported video format")
    
    # Save the file
    file_path = f"data/videos/{task_id}{file_extension}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {
        "task_id": task_id,
        "filename": file.filename,
        "upload_time": datetime.now().isoformat(),
        "status": "uploaded"
    }

@router.get("/status/{task_id}")
async def get_subtitle_status(task_id: str):
    """
    Get the status of a subtitle processing task
    """
    # Check status from database or file system
    # This is a placeholder - actual implementation would check real status
    return subtitle_service.get_task_status(task_id)

@router.get("/download/{task_id}")
async def download_processed_subtitle(task_id: str):
    """
    Download the processed subtitle file
    """
    file_path = f"data/processed/{task_id}.srt"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Processed file not found")
    
    return FileResponse(
        path=file_path, 
        filename=f"processed_{task_id}.srt",
        media_type="application/octet-stream"
    )
