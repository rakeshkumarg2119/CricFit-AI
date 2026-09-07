from datetime import datetime
from config import ALLOWED_VIDEO_TYPES, MAX_VIDEO_SIZE_MB

def validate_video_file(uploaded_file):
    """
    Validate uploaded video file against allowed extensions and size limit.
    Returns (is_valid: bool, message: str)
    """
    if uploaded_file is None:
        return False, "No file selected."
    
    file_ext = uploaded_file.name.split(".")[-1].lower()
    if file_ext not in ALLOWED_VIDEO_TYPES:
        return False, f"Unsupported file format '.{file_ext}'. Allowed formats: {', '.join(ALLOWED_VIDEO_TYPES).upper()}"
    
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_VIDEO_SIZE_MB:
        return False, f"File size ({size_mb:.1f} MB) exceeds maximum limit of {MAX_VIDEO_SIZE_MB} MB."
    
    return True, "File valid."


def format_file_size(size_bytes):
    """Format bytes into readable MB string."""
    if not size_bytes:
        return "0 MB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def get_score_status(score):
    """
    Map score to readable status text and visual indicator specs.
    Returns dictionary with text status, color, and emoji.
    """
    if score >= 80:
        return {
            "status": "Excellent",
            "color": "#10B981", # Emerald green
            "bg": "#064E3B",
            "emoji": "🌟",
            "priority": "Low"
        }
    elif score >= 70:
        return {
            "status": "Good",
            "color": "#06B6D4", # Cyan
            "bg": "#164E63",
            "emoji": "👍",
            "priority": "Medium"
        }
    elif score >= 60:
        return {
            "status": "Average",
            "color": "#F59E0B", # Amber
            "bg": "#78350F",
            "emoji": "⚠️",
            "priority": "High"
        }
    else:
        return {
            "status": "Needs Improvement",
            "color": "#EF4444", # Red
            "bg": "#7F1D1D",
            "emoji": "🚨",
            "priority": "High"
        }


def get_formatted_date():
    """Returns current date formatted nicely."""
    return datetime.now().strftime("%d %b %Y")
