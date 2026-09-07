"""
CricFit AI — Database Service
=============================
Handles MongoDB connections and document storage for raw ML model outputs,
Groq LLM enriched reports, injury screenings, and user progress history.
Includes automatic local in-memory fallback if MongoDB is not running.
"""

import os
import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "cricfit_ai")

_client = None
_db = None

# In-memory storage fallback for seamless local operation without MongoDB
_local_raw_reports: List[Dict[str, Any]] = []
_local_fitness_reports: List[Dict[str, Any]] = []


def get_db():
    """
    Return a MongoDB database handle, or None if unavailable.
    Re-attempts connection on each call if previously failed,
    so a transient outage is recovered automatically.
    """
    global _client, _db

    if _db is not None:
        return _db

    try:
        from pymongo import MongoClient
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        _client.admin.command("ping")  # force-verify the connection
        _db = _client[MONGODB_DATABASE]
        print(f"[INFO] Connected to MongoDB: {MONGODB_URI} / {MONGODB_DATABASE}")
    except Exception as e:
        # Expected if MongoDB server is not running locally
        _client = None
        _db = None

    return _db


def reset_db():
    """Call this to force a reconnection attempt on the next get_db() call."""
    global _client, _db
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _db = None


def save_raw_model_report(user_id: str, activity: str, raw_output: Dict[str, Any]) -> str:
    """
    Step 1: Saves the raw ML model inference result to database immediately.
    Returns: doc_id
    """
    doc = {
        "user_id": user_id or "anonymous",
        "activity": activity.lower(),
        "stage": "raw_ml_inference",
        "raw_output": raw_output,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    db = get_db()
    if db is not None:
        try:
            result = db.raw_model_reports.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"[WARN] Failed to insert raw model report in MongoDB: {e}")

    # Fallback to in-memory list
    _local_raw_reports.append(doc)
    return f"local_raw_{len(_local_raw_reports)}"


def save_final_report(report_data: Dict[str, Any], user_id: str = "anonymous") -> str:
    """
    Step 2: Saves the full enriched report (including Groq insights and PDF path).
    """
    doc = dict(report_data)
    doc["user_id"] = user_id or "anonymous"
    doc["saved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    db = get_db()
    if db is not None:
        try:
            result = db.fitness_reports.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"[WARN] Failed to save final report to MongoDB: {e}")

    _local_fitness_reports.append(doc)
    return str(doc.get("id", f"local_fit_{len(_local_fitness_reports)}"))


def get_user_fitness_reports(user_id: str = "anonymous", activity: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves fitness reports for a given user."""
    db = get_db()
    if db is not None:
        try:
            query = {"user_id": user_id}
            if activity:
                query["activity"] = activity.lower()
            reports = list(db.fitness_reports.find(query).sort("timestamp", -1))
            for r in reports:
                r["_id"] = str(r["_id"])
            return reports
        except Exception as e:
            print(f"[WARN] Failed to fetch fitness reports from MongoDB: {e}")

    # Fallback from in-memory
    results = [r for r in _local_fitness_reports if r.get("user_id") == user_id]
    if activity:
        results = [r for r in results if r.get("activity") == activity.lower()]
    return list(reversed(results))
