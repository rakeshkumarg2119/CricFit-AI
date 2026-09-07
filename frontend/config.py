import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or frontend directory if available
_root_env = Path(__file__).resolve().parent.parent / ".env"
if _root_env.is_file():
    load_dotenv(dotenv_path=_root_env)
_local_env = Path(__file__).resolve().parent / ".env"
if _local_env.is_file():
    load_dotenv(dotenv_path=_local_env)
load_dotenv()

# App Branding
APP_NAME = "CRICFIT AI"
APP_TAGLINE = "Your AI-Powered Cricket Fitness Coach"
APP_SUBTITLE = "Analyze your cricket movement, understand your physical performance, and get personalized fitness insights powered by AI."
SECONDARY_TAGLINE = "Upload. Analyze. Improve."

# Server & API Settings
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Database Settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "cricfit_ai")

# Video Settings
ALLOWED_VIDEO_TYPES = ["mp4", "mov", "avi"]
MAX_VIDEO_SIZE_MB = 100

# Available Navigation Pages
PAGES = {
    "LOGIN": "login",
    "HOME": "home",
    "BATTING": "batting",
    "BOWLING": "bowling",
    "YOYO": "yoyo",
    "INJURY_DETECTION": "injury_detection",
    "REPORTS": "reports",
    "PROGRESS": "progress",
    "PROFILE": "profile",
}
