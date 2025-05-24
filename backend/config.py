import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
VIDEO_DIR = DATA_DIR / "videos"
STATUS_DIR = DATA_DIR / "status"

# Create required directories
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
STATUS_DIR.mkdir(parents=True, exist_ok=True)

# API Settings
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# AWS Settings (from environment variables)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# AWS Service Configuration
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "videosubtitlecleanser-data")
AWS_TRANSCRIBE_LANGUAGE_CODE = os.getenv("AWS_TRANSCRIBE_LANGUAGE_CODE", "en-US")

# Processing Settings
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_SUBTITLE_EXTENSIONS = ['.srt', '.vtt', '.sub', '.sbv', '.smi', '.ssa', '.ass']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv']
DEFAULT_OUTPUT_FORMAT = "vtt"

# Language Settings
DEFAULT_LANGUAGE = "en"
DEFAULT_TRANSLATION_QUALITY = "standard"
