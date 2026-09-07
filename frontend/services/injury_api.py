"""
CricFit AI — Frontend Injury API Service
Centralised layer between Streamlit pages and the FastAPI backend.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Read from environment; falls back to localhost:8000
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Timeout in seconds for the backend call
_TIMEOUT = 30


def _backend_url() -> str:
    """Always return a clean base URL (no trailing slash)."""
    return BACKEND_URL.rstrip("/")


def check_backend_health() -> bool:
    """Return True if the FastAPI backend is reachable."""
    try:
        r = requests.get(f"{_backend_url()}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def analyze_injury(
    user_id: str,
    symptoms: list,
    custom_description: str,
    pain_intensity: float,
    duration: str,
    activity_context: str,
) -> tuple:
    """
    POST /injury/analyze to the FastAPI backend.

    Returns:
        (success: bool, data: dict | None, error_message: str | None)
    """
    # ------------------------------------------------------------------ #
    # Client-side validation before even hitting the network              #
    # ------------------------------------------------------------------ #
    if not symptoms and not custom_description.strip():
        return (
            False,
            None,
            "Please select at least one symptom or describe your symptoms.",
        )

    if not (0 <= pain_intensity <= 10):
        return False, None, "Pain intensity must be between 0 and 10."

    if not duration:
        return False, None, "Please select a duration."

    if not activity_context:
        return False, None, "Please select when the symptoms occur."

    # ------------------------------------------------------------------ #
    # Send to backend                                                     #
    # ------------------------------------------------------------------ #
    url = f"{_backend_url()}/injury/analyze"
    payload = {
        "user_id": str(user_id) if user_id else "anonymous",
        "symptoms": symptoms,
        "custom_description": custom_description,
        "pain_intensity": float(pain_intensity),
        "duration": duration,
        "activity_context": activity_context,
    }

    try:
        response = requests.post(url, json=payload, timeout=_TIMEOUT)

        # ---- 200 OK ----
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                return False, None, "The service returned an unreadable response. Please try again."

            if data.get("success"):
                return True, data, None
            else:
                return False, None, data.get("message", "Analysis failed. Please try again.")

        # ---- 422 Validation error from FastAPI ----
        if response.status_code == 422:
            try:
                detail = response.json().get("detail", "")
                if isinstance(detail, list):
                    msgs = [d.get("msg", "") for d in detail]
                    detail = "; ".join(msgs)
            except Exception:
                detail = "Invalid input."
            return False, None, f"Validation error: {detail}"

        # ---- Other HTTP errors ----
        return (
            False,
            None,
            f"The analysis service returned an unexpected response (HTTP {response.status_code}). Please try again.",
        )

    except requests.exceptions.ConnectionError:
        return (
            False,
            None,
            "Unable to connect to the injury analysis service right now. "
            "Please ensure the backend is running and try again.",
        )
    except requests.exceptions.Timeout:
        return (
            False,
            None,
            "The injury analysis service took too long to respond. Please try again.",
        )
    except Exception:
        return (
            False,
            None,
            "An unexpected error occurred while contacting the analysis service. Please try again.",
        )


def get_injury_reports(user_id: str) -> list:
    """Fetch saved injury reports for a user from the backend."""
    try:
        url = f"{_backend_url()}/injury/reports/{user_id}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []
