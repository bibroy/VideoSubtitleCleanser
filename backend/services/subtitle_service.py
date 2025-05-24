import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Dictionary to store task statuses in memory (would be a database in production)
task_status = {}

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a specific task
    """
    if task_id in task_status:
        return task_status[task_id]
    
    # Look for status file
    status_path = Path(f"data/status/{task_id}.json")
    if status_path.exists():
        with open(status_path, "r") as f:
            return json.load(f)
    
    return {
        "task_id": task_id,
        "status": "not_found",
        "message": "Task not found or expired"
    }

def update_task_status(task_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Update the status of a task
    """
    if details is None:
        details = {}
        
    task_status[task_id] = {
        "task_id": task_id,
        "status": status,
        "last_updated": datetime.now().isoformat(),
        **details
    }
    
    # Also save to file for persistence
    os.makedirs("data/status", exist_ok=True)
    with open(f"data/status/{task_id}.json", "w") as f:
        json.dump(task_status[task_id], f)

def get_subtitle_path(task_id: str, original: bool = True) -> Optional[str]:
    """
    Get the path to a subtitle file based on task_id
    """
    if original:
        base_dir = "data/uploads"
    else:
        base_dir = "data/processed"
    
    # Check for files with different extensions
    for ext in ['.srt', '.vtt', '.sub', '.sbv', '.smi', '.ssa', '.ass']:
        file_path = f"{base_dir}/{task_id}{ext}"
        if os.path.exists(file_path):
            return file_path
    
    return None

def get_video_path(task_id: str) -> Optional[str]:
    """
    Get the path to a video file based on task_id
    """
    base_dir = "data/videos"
    
    # Check for files with different extensions
    for ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']:
        file_path = f"{base_dir}/{task_id}{ext}"
        if os.path.exists(file_path):
            return file_path
    
    return None
