"""
CRICFIT AI — Frontend Response Parser & Validator
=================================================
Validates backend response payloads and guarantees full schema integrity
for the Biomechanical Radar, Plain-Language Groq Insights, Exercise Plan,
Diet Guidelines, and Media links.
"""

import uuid
from datetime import datetime


def parse_analysis_response(raw_json: dict, activity_type: str = "batting") -> tuple:
    """
    Validates and structures raw backend JSON into standard report format.
    Returns: (success: bool, data: dict, message: str)
    """
    if not isinstance(raw_json, dict):
        return False, None, "The AI returned an invalid response format."

    # Validate overall score
    overall_score = raw_json.get("overall_score")
    if overall_score is None:
        return False, None, "Analysis result is incomplete (missing overall score)."

    try:
        overall_score = int(overall_score)
    except (ValueError, TypeError):
        return False, None, "Analysis result returned an invalid score."

    # Validate metrics dictionary
    raw_metrics = raw_json.get("metrics")
    if not isinstance(raw_metrics, dict):
        raw_metrics = raw_json

    required_metric_keys = [
        "balance",
        "lower_body_stability",
        "hip_mobility",
        "core_stability",
        "coordination",
        "body_symmetry",
        "movement_quality"
    ]

    metrics = {}
    for key in required_metric_keys:
        val = raw_metrics.get(key, raw_json.get(key, 75))
        try:
            metrics[key] = int(val)
        except (ValueError, TypeError):
            metrics[key] = 75

    # Strengths
    strengths_raw = raw_json.get("strengths", [])
    strengths = [str(s) for s in strengths_raw] if isinstance(strengths_raw, list) else []

    # Areas to improve
    areas_raw = raw_json.get("areas_to_improve", [])
    areas_to_improve = []
    if isinstance(areas_raw, list):
        for item in areas_raw:
            if isinstance(item, dict):
                areas_to_improve.append({
                    "area": str(item.get("area", "Technique")),
                    "score": int(item.get("score", metrics.get("movement_quality", overall_score))),
                    "priority": str(item.get("priority", "Medium")),
                    "explanation": str(item.get("explanation", item.get("impact", "")))
                })
            elif isinstance(item, str):
                areas_to_improve.append({
                    "area": item,
                    "score": metrics.get("movement_quality", overall_score),
                    "priority": "Medium",
                    "explanation": f"Conditioning priority: {item}"
                })

    # Groq Plain-Language Summary
    ai_summary = raw_json.get("ai_summary", "")
    if not ai_summary:
        ai_summary = f"Performance assessment completed for {activity_type.title()}."

    # Prescribed Exercises (Groq structure)
    exercises = raw_json.get("exercises", [])
    if not isinstance(exercises, list) or not exercises:
        # Fallback to recommendations
        recs = raw_json.get("recommendations", [])
        exercises = []
        for r in recs:
            if isinstance(r, dict):
                exercises.append({
                    "exercise_name": r.get("exercise", "Drill"),
                    "target_area": r.get("target", "Biomechanics"),
                    "sets_and_reps": f"{r.get('sets', '3')} sets × {r.get('duration', '30s')}",
                    "difficulty": r.get("difficulty", "Standard"),
                    "how_it_improves": r.get("reason", "Enhances kinetic movement efficiency.")
                })

    # Recommendations (compatibility format)
    recommendations = raw_json.get("recommendations", [])
    if not recommendations and exercises:
        recommendations = [
            {
                "exercise": e.get("exercise_name", "Drill"),
                "target": e.get("target_area", "Biomechanics"),
                "sets": "3",
                "duration": e.get("sets_and_reps", "30s"),
                "difficulty": e.get("difficulty", "Standard"),
                "reason": e.get("how_it_improves", "Enhances athletic performance.")
            }
            for e in exercises
        ]

    # Nutrition Plan
    nutrition_plan = raw_json.get("nutrition_plan", {})
    if not isinstance(nutrition_plan, dict):
        nutrition_plan = {}

    activity = str(raw_json.get("activity", activity_type)).lower()

    report = {
        "id": str(raw_json.get("id", f"REP-{uuid.uuid4().hex[:8].upper()}")),
        "timestamp": str(raw_json.get("timestamp", datetime.now().isoformat())),
        "date_str": str(raw_json.get("date_str", datetime.now().strftime("%d %b %Y, %I:%M %p"))),
        "activity": activity,
        "overall_score": overall_score,
        "movement_quality": metrics["movement_quality"],
        "risk_level": str(raw_json.get("risk_level", "Low")).title(),
        "metrics": metrics,
        "strengths": strengths,
        "areas_to_improve": areas_to_improve,
        "ai_summary": ai_summary,
        "technique_analysis": raw_json.get("technique_analysis", ""),
        "exercises": exercises,
        "recommendations": recommendations,
        "how_following_improves": raw_json.get("how_following_improves", ""),
        "nutrition_plan": nutrition_plan,
        "annotated_video_url": raw_json.get("annotated_video_url"),
        "pdf_url": raw_json.get("pdf_url"),
    }

    # Attach model specific badges
    if "shot_classification" in raw_json:
        report["shot_classification"] = raw_json["shot_classification"]
    if "arm_classification" in raw_json:
        report["arm_classification"] = raw_json["arm_classification"]
    if "pace_classification" in raw_json:
        report["pace_classification"] = raw_json["pace_classification"]
    if "closest_pro_match" in raw_json:
        report["closest_pro_match"] = raw_json["closest_pro_match"]
    if "shuttle_metrics" in raw_json:
        report["shuttle_metrics"] = raw_json["shuttle_metrics"]
    if "rest_compliance" in raw_json:
        report["rest_compliance"] = raw_json["rest_compliance"]
    if "level_reference" in raw_json:
        report["level_reference"] = raw_json["level_reference"]

    return True, report, "Analysis completed successfully!"
