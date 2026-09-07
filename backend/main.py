"""
CRICFIT AI — Unified FastAPI Backend
====================================
Exposes endpoints for:
- Video Upload & AI Vision Biomechanical Analysis (Batting, Bowling, Yo-Yo)
- Groq LLM Plain-Language Interpretation, Drills & Nutrition Planning
- PDF Report Generation & Annotated Video Serving
- Sports Injury Screening & Report Storage
"""

import os
import sys
import uuid
import shutil
import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

load_dotenv()

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import Backend Services
from database import (
    get_db,
    save_raw_model_report,
    save_final_report,
    get_user_fitness_reports,
    delete_fitness_report,
)
from injury_service import analyze as analyze_injury
from groq_service import generate_llm_insights
from pdf_service import generate_pdf_report, PDF_REPORTS_DIR
from model_service import analyze_batting, analyze_bowling, analyze_yoyo, OUTPUTS_DIR, VIDEOS_DIR
from schema_adapter import adapt_to_unified_report

# Ensure output directories exist
TEMP_UPLOADS_DIR = BACKEND_DIR / "temp_uploads"
TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
Path(OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
Path(VIDEOS_DIR).mkdir(parents=True, exist_ok=True)
Path(PDF_REPORTS_DIR).mkdir(parents=True, exist_ok=True)

# App Instance
app = FastAPI(title="CRICFIT AI Unified Backend", version="2.0.0")

# Mount Static Outputs for streaming annotated videos and downloading PDFs
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "CRICFIT AI Backend",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


# ============================================================================
# Core Video Biomechanics & Groq Analysis Endpoint
# ============================================================================
@app.post("/analyze")
def analyze_video_endpoint(
    video: UploadFile = File(...),
    activity_type: str = Form("batting"),
    yoyo_level: Optional[str] = Form(None),
    user_id: Optional[str] = Form("anonymous"),
):
    """
    Unified end-to-end pipeline:
    1. Saves video upload.
    2. Runs CV/ML Model (Batting / Bowling / Yo-Yo).
    3. Saves raw model JSON to database first.
    4. Passes telemetry to Groq LLM (Plain-text insights, Drills, Food Plan).
    5. Generates printable PDF report.
    6. Returns structured response with text format, metrics, and media URLs.
    Executed in FastAPI background threadpool to avoid blocking main event loop.
    """
    activity = activity_type.strip().lower()
    valid_activities = ["batting", "bowling", "yoyo", "yoyo_test"]
    if activity not in valid_activities:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid activity_type '{activity_type}'. Must be one of: {valid_activities}"
        )

    # Save uploaded video file locally for model consumption
    file_ext = Path(video.filename or "upload.mp4").suffix or ".mp4"
    temp_filename = f"upload_{uuid.uuid4().hex[:10]}{file_ext}"
    temp_path = TEMP_UPLOADS_DIR / temp_filename

    try:
        with open(temp_path, "wb") as f:
            content = video.file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video upload: {e}")

    try:
        annotated_video_path = None
        raw_output = {}

        # ── 1. Model Inference ────────────────────────────────────────────────
        if activity == "batting":
            raw_output, annotated_video_path = analyze_batting(str(temp_path), generate_video=True)
        elif activity == "bowling":
            raw_output, annotated_video_path = analyze_bowling(str(temp_path), generate_video=True)
        else:  # Yo-Yo
            manual_input = {"yoyo_level": yoyo_level or "16.5"}
            raw_output, annotated_video_path = analyze_yoyo(str(temp_path), manual_input=manual_input)

        if not raw_output or "error" in raw_output:
            err_msg = raw_output.get("error", "Pose detection or model analysis failed.")
            raise HTTPException(status_code=400, detail=err_msg)

        # ── 2. Database First: Save Raw Output ────────────────────────────────
        raw_doc_id = save_raw_model_report(user_id=user_id, activity=activity, raw_output=raw_output)

        # ── 3. Groq LLM Intelligence Layer ──────────────────────────────────
        llm_insights = generate_llm_insights(activity_type=activity, model_output=raw_output)

        # ── 4. Build Static Media URLs ────────────────────────────────────────
        report_id = f"CF-{uuid.uuid4().hex[:8].upper()}"
        
        video_url = None
        if annotated_video_path and os.path.exists(annotated_video_path):
            rel_video = os.path.relpath(annotated_video_path, str(OUTPUTS_DIR)).replace("\\", "/")
            video_url = f"/outputs/{rel_video}"

        # ── 5. Generate PDF Report ────────────────────────────────────────────
        # Temporary unified representation for PDF builder
        interim_report = adapt_to_unified_report(
            activity_type=activity,
            raw_model_output=raw_output,
            llm_insights=llm_insights,
            video_url=video_url,
            report_id=report_id
        )
        pdf_file_path = generate_pdf_report(interim_report)
        
        pdf_url = None
        if pdf_file_path and os.path.exists(pdf_file_path):
            rel_pdf = os.path.relpath(pdf_file_path, str(OUTPUTS_DIR)).replace("\\", "/")
            pdf_url = f"/outputs/{rel_pdf}"

        # ── 6. Final Unified Schema & Persistence ─────────────────────────────
        final_report = adapt_to_unified_report(
            activity_type=activity,
            raw_model_output=raw_output,
            llm_insights=llm_insights,
            video_url=video_url,
            pdf_url=pdf_url,
            report_id=report_id
        )
        final_report["raw_db_id"] = raw_doc_id
        save_final_report(final_report, user_id=user_id)

        return final_report

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Video analysis pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal analysis failure: {str(e)}")
    finally:
        # Clean up temporary uploaded raw video
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.get("/reports/{user_id}")
def get_user_reports_endpoint(user_id: str, activity: Optional[str] = None):
    """Retrieves all past fitness reports for a user, sorted newest-first."""
    return get_user_fitness_reports(user_id=user_id, activity=activity)


@app.delete("/reports/{user_id}/{report_id}")
def delete_report_endpoint(user_id: str, report_id: str):
    """Deletes a specific fitness report by its ID."""
    deleted = delete_fitness_report(report_id=report_id, user_id=user_id)
    if deleted:
        return {"status": "deleted", "report_id": report_id}
    raise HTTPException(status_code=404, detail="Report not found or not authorized to delete.")


@app.get("/download/pdf/{report_id}")
def download_pdf_endpoint(report_id: str):
    """Directly downloads a generated PDF report."""
    if os.path.exists(PDF_REPORTS_DIR):
        for fname in os.listdir(PDF_REPORTS_DIR):
            if report_id in fname and fname.endswith(".pdf"):
                file_path = os.path.join(PDF_REPORTS_DIR, fname)
                return FileResponse(file_path, media_type="application/pdf", filename=fname)
    raise HTTPException(status_code=404, detail=f"PDF report for {report_id} not found.")



# ============================================================================
# Injury Screening Endpoints
# ============================================================================
class InjuryRequest(BaseModel):
    user_id: str = "anonymous"
    symptoms: List[str] = []
    custom_description: str = ""
    pain_intensity: float = 0.0
    duration: str = "Less than 1 day"
    activity_context: str = "Other"

    @field_validator("pain_intensity")
    @classmethod
    def validate_pain(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("pain_intensity must be between 0 and 10")
        return v


@app.post("/injury/analyze")
def analyze_injury_endpoint(req: InjuryRequest):
    if not req.symptoms and not req.custom_description.strip():
        raise HTTPException(
            status_code=422,
            detail="Please provide at least one symptom or a custom description.",
        )

    valid_durations = [
        "Less than 1 day", "1–3 days", "Less than 1 week",
        "1–2 weeks", "More than 2 weeks", "More than 1 month",
    ]
    normalised_duration = req.duration.replace("-", "–")
    if normalised_duration not in valid_durations:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid duration. Must be one of: {valid_durations}",
        )
    req = req.model_copy(update={"duration": normalised_duration})

    valid_contexts = [
        "During batting", "During bowling", "During running",
        "During training", "During rest", "After training", "Other",
    ]
    if req.activity_context not in valid_contexts:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid activity context. Must be one of: {valid_contexts}",
        )

    try:
        analysis_result = analyze_injury(
            req.symptoms,
            req.custom_description,
            req.pain_intensity,
            req.duration,
            req.activity_context,
        )
    except Exception as e:
        print(f"[ERROR] injury_service.analyze failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again.",
        )

    analysis_result["symptoms"] = req.symptoms
    analysis_result["custom_description"] = req.custom_description
    analysis_result["pain_intensity"] = req.pain_intensity
    analysis_result["duration"] = req.duration
    analysis_result["activity_context"] = req.activity_context

    db_save_status = "saved"
    db = get_db()
    if db is not None:
        try:
            report = {
                "user_id": req.user_id,
                "activity": "Injury Screening",
                "symptoms": req.symptoms,
                "custom_description": req.custom_description,
                "pain_intensity": req.pain_intensity,
                "duration": req.duration,
                "activity_context": req.activity_context,
                "analysis_result": analysis_result,
                "stage": analysis_result["stage"],
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            db.injury_reports.insert_one(report)
        except Exception as e:
            print(f"[WARN] Failed to save injury report to MongoDB: {e}")
            db_save_status = "not_saved"
    else:
        db_save_status = "unavailable"

    analysis_result["db_save_status"] = db_save_status
    return analysis_result


@app.get("/injury/reports/{user_id}")
def get_injury_reports_endpoint(user_id: str):
    db = get_db()
    if db is None:
        return []
    try:
        reports = list(
            db.injury_reports.find({"user_id": user_id}).sort("created_at", -1)
        )
        for r in reports:
            r["_id"] = str(r["_id"])
        return reports
    except Exception as e:
        print(f"[WARN] Failed to fetch injury reports: {e}")
        return []
