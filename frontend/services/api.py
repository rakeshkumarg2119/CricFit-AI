"""
CRICFIT AI — Frontend API Client Service
========================================
Connects Streamlit frontend to FastAPI backend for:
- Video Biomechanical Analysis (Batting, Bowling, Yo-Yo)
- Groq AI Intelligence & Nutrition Plans
- PDF Report Downloads
- Health Checks
"""

import requests
import streamlit as st
from config import BACKEND_URL
from services.parser import parse_analysis_response


def analyze_video(video_file, activity_type="batting", yoyo_level=None, user_id=None):
    """
    Send the uploaded video file to the FastAPI backend AI vision model & Groq LLM pipeline.
    Endpoint: POST /analyze
    Payload:
      - video: multipart file
      - activity_type: 'batting', 'bowling', or 'yoyo'
      - yoyo_level: optional string (e.g. '16.5')
      - user_id: optional user identifier
    
    Returns tuple: (success: bool, data: dict, message: str)
    """
    try:
        url = f"{BACKEND_URL.rstrip('/')}/analyze"
        
        # Prepare file payload
        video_bytes = video_file.getvalue() if hasattr(video_file, "getvalue") else video_file.read()
        file_type = getattr(video_file, "type", "video/mp4") or "video/mp4"
        file_name = getattr(video_file, "name", "upload.mp4") or "upload.mp4"
        
        files = {
            "video": (file_name, video_bytes, file_type)
        }
        
        current_user = user_id or st.session_state.get("user", {}).get("username", "anonymous")
        data = {
            "activity_type": str(activity_type).lower(),
            "user_id": str(current_user)
        }
        if yoyo_level:
            data["yoyo_level"] = str(yoyo_level)
        
        # Generous timeout for deep vision + Groq processing
        response = requests.post(url, files=files, data=data, timeout=120)
        
        if response.status_code == 200:
            try:
                raw_json = response.json()
            except Exception:
                return False, None, "The AI returned an unparseable response format."
                
            return parse_analysis_response(raw_json, activity_type=activity_type)
        else:
            try:
                err_detail = response.json().get("detail", "Analysis failed.")
            except Exception:
                err_detail = f"Server error ({response.status_code})"
            return False, None, f"Analysis Error: {err_detail}"
            
    except requests.exceptions.Timeout:
        return False, None, "The video analysis timed out. Please try a shorter video clip."
    except requests.exceptions.ConnectionError:
        return False, None, "AI backend service is unreachable. Please verify the backend server is running."
    except Exception as e:
        return False, None, f"Unable to analyze video: {str(e)}"
