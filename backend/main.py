import datetime
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Use direct (non-package-relative) imports so this file can be run as:
#   uvicorn backend.main:app --reload   (from project root)
# or
#   uvicorn main:app --reload           (from backend/ directory)
# ---------------------------------------------------------------------------
try:
    from backend.database import get_db
    from backend.injury_service import analyze
except ModuleNotFoundError:
    from database import get_db        # type: ignore
    from injury_service import analyze  # type: ignore

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="CRICFIT AI Backend", version="1.0.0")

# ---------------------------------------------------------------------------
# CORS — allow Streamlit (localhost:8501) to talk to FastAPI (localhost:8000)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handler — never expose raw tracebacks
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal error occurred. Please try again later.",
        },
    )


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class InjuryRequest(BaseModel):
    user_id: str = "anonymous"
    symptoms: List[str] = []
    custom_description: str = ""
    pain_intensity: float = 0.0          # float — frontend sends e.g. 7.5
    duration: str = "Less than 1 day"
    activity_context: str = "Other"

    @field_validator("symptoms")
    @classmethod
    def at_least_one_input(cls, v):
        # Cross-field validation happens in the endpoint; symptom list can be empty
        # if custom_description is provided.
        return v

    @field_validator("pain_intensity")
    @classmethod
    def validate_pain(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("pain_intensity must be between 0 and 10")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "CRICFIT AI Backend"}


@app.post("/injury/analyze")
def analyze_injury_endpoint(req: InjuryRequest):
    # --- Validate: need at least one symptom OR a custom description ---
    if not req.symptoms and not req.custom_description.strip():
        raise HTTPException(
            status_code=422,
            detail="Please provide at least one symptom or a custom description.",
        )

    # --- Validate duration (normalise en-dash ↔ ASCII hyphen before checking) ---
    valid_durations = [
        "Less than 1 day", "1–3 days", "Less than 1 week",
        "1–2 weeks", "More than 2 weeks", "More than 1 month",
    ]
    # Normalise: replace ASCII hyphens with en-dashes so both variants match
    normalised_duration = req.duration.replace("-", "–")
    if normalised_duration not in valid_durations:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid duration. Must be one of: {valid_durations}",
        )
    # Use the normalised form for downstream logic
    req = req.model_copy(update={"duration": normalised_duration})

    # --- Validate activity context ---
    valid_contexts = [
        "During batting", "During bowling", "During running",
        "During training", "During rest", "After training", "Other",
    ]
    if req.activity_context not in valid_contexts:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid activity context. Must be one of: {valid_contexts}",
        )

    # --- Run analysis ---
    try:
        analysis_result = analyze(
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

    # Enrich response with the echoed request fields so the frontend
    # can render them in the report without re-passing them separately.
    analysis_result["symptoms"] = req.symptoms
    analysis_result["custom_description"] = req.custom_description
    analysis_result["pain_intensity"] = req.pain_intensity
    analysis_result["duration"] = req.duration
    analysis_result["activity_context"] = req.activity_context

    # --- Persist to MongoDB (non-blocking on failure) ---
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
            print(f"[WARN] Failed to save report to MongoDB: {e}")
            db_save_status = "not_saved"
    else:
        db_save_status = "unavailable"

    analysis_result["db_save_status"] = db_save_status
    return analysis_result


@app.get("/injury/reports/{user_id}")
def get_injury_reports(user_id: str):
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
        print(f"[WARN] Failed to fetch reports: {e}")
        return []
