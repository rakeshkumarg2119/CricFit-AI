import requests
import streamlit as st
from config import BACKEND_URL
from services.parser import parse_analysis_response

def analyze_video(video_file, activity_type="batting"):
    """
    Send the real uploaded video file to the FastAPI backend AI model.
    Endpoint: POST /analyze
    Request payload:
      - video: multipart file
      - activity_type: 'batting' or 'bowling'
    
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
        data = {
            "activity_type": str(activity_type).lower()
        }
        
        response = requests.post(url, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            try:
                raw_json = response.json()
            except Exception:
                return False, None, "The AI returned an invalid analysis response."
                
            return parse_analysis_response(raw_json, activity_type=activity_type)
        else:
            return False, None, "Unable to analyze this video. Please try again."
            
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False, None, "AI analysis service is unavailable. Please make sure the backend is running."
    except Exception as e:
        return False, None, "Unable to analyze this video. Please try again."
