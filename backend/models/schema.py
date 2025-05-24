from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    TRANSLATING = "translating"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"

class SubtitleFormat(str, Enum):
    SRT = "srt"
    VTT = "vtt"
    SUB = "sub"
    SBV = "sbv"
    SMI = "smi"
    SSA = "ssa"
    ASS = "ass"

class VideoFormat(str, Enum):
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    WMV = "wmv"

class ProcessingOptions(BaseModel):
    cleanse_errors: bool = True
    correct_grammar: bool = True
    remove_invalid_chars: bool = True
    correct_timing: bool = True
    optimize_position: bool = True
    target_language: Optional[str] = None
    diarize_speakers: bool = False
    use_aws_transcribe: bool = False
    max_speakers: int = 10
    enforce_font_consistency: bool = True
    remove_duplicate_lines: bool = True
    output_format: str = "vtt"

class TranslationRequest(BaseModel):
    task_id: str
    source_language: Optional[str] = None  # Auto-detect if not provided
    target_language: str
    preserve_formatting: bool = True
    quality: str = "standard"  # standard, premium

class SubtitleTask(BaseModel):
    task_id: str
    filename: str
    upload_time: datetime = Field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.UPLOADED
    processing_options: Optional[ProcessingOptions] = None
    progress: int = 0
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None

class SubtitleAnalysis(BaseModel):
    task_id: str
    issues: List[Dict[str, Any]] = []
    statistics: Dict[str, Any] = {}
    recommendations: List[Dict[str, Any]] = []
    error: Optional[str] = None
