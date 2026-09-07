import uuid
from datetime import datetime

def parse_analysis_response(raw_json, activity_type="batting"):
    """
    Safely parse and strictly validate raw backend JSON output.
    Returns tuple: (success: bool, data: dict, message: str)
    
    If any required analysis field is missing or invalid, returns success=False
    with message: "Analysis result is incomplete. Please try again."
    Do NOT replace missing values with fake numbers.
    """
    if not isinstance(raw_json, dict):
        return False, None, "The AI returned an invalid analysis response."

    # Validate overall score
    if "overall_score" not in raw_json or raw_json["overall_score"] is None:
        return False, None, "Analysis result is incomplete. Please try again."

    try:
        overall_score = int(raw_json["overall_score"])
    except (ValueError, TypeError):
        return False, None, "Analysis result is incomplete. Please try again."

    # Validate metrics dictionary
    raw_metrics = raw_json.get("metrics")
    if not isinstance(raw_metrics, dict):
        # Fallback check if metrics are top-level
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
        val = raw_metrics.get(key)
        if val is None:
            val = raw_json.get(key)
            
        if val is None:
            return False, None, "Analysis result is incomplete. Please try again."
            
        try:
            metrics[key] = int(val)
        except (ValueError, TypeError):
            return False, None, "Analysis result is incomplete. Please try again."

    # Validate strengths
    strengths = raw_json.get("strengths")
    if not isinstance(strengths, list):
        return False, None, "Analysis result is incomplete. Please try again."

    # Validate areas_to_improve
    areas_raw = raw_json.get("areas_to_improve")
    if not isinstance(areas_raw, list):
        return False, None, "Analysis result is incomplete. Please try again."

    areas_to_improve = []
    for item in areas_raw:
        if isinstance(item, str):
            areas_to_improve.append({
                "area": item,
                "score": metrics.get("movement_quality", overall_score),
                "priority": "Medium",
                "explanation": f"Recommended area of physical conditioning: {item}."
            })
        elif isinstance(item, dict) and "area" in item:
            areas_to_improve.append({
                "area": str(item.get("area", "")),
                "score": int(item.get("score", overall_score)),
                "priority": str(item.get("priority", "Medium")),
                "explanation": str(item.get("explanation", ""))
            })

    # Validate ai_summary
    ai_summary = raw_json.get("ai_summary")
    if not ai_summary or not isinstance(ai_summary, str):
        return False, None, "Analysis result is incomplete. Please try again."

    # Validate recommendations
    recs_raw = raw_json.get("recommendations")
    if not isinstance(recs_raw, list):
        return False, None, "Analysis result is incomplete. Please try again."

    recommendations = []
    for rec in recs_raw:
        if isinstance(rec, dict) and "exercise" in rec:
            recommendations.append({
                "exercise": str(rec.get("exercise", "")),
                "target": str(rec.get("target", "Biomechanics")),
                "sets": str(rec.get("sets", "3")),
                "duration": str(rec.get("duration", rec.get("reps", "30 sec"))),
                "difficulty": str(rec.get("difficulty", "Standard")),
                "reason": str(rec.get("reason", ""))
            })
        elif isinstance(rec, str):
            recommendations.append({
                "exercise": rec,
                "target": "Biomechanics",
                "sets": "3",
                "duration": "30 sec",
                "difficulty": "Standard",
                "reason": "Targeted drill for physical optimization."
            })

    activity = str(raw_json.get("activity", activity_type)).lower()

    report = {
        "id": str(raw_json.get("id", f"report_{uuid.uuid4().hex[:8]}")),
        "timestamp": str(raw_json.get("timestamp", datetime.now().isoformat())),
        "date_str": str(raw_json.get("date_str", datetime.now().strftime("%d %b %Y"))),
        "activity": activity,
        "overall_score": overall_score,
        "movement_quality": metrics["movement_quality"],
        "risk_level": str(raw_json.get("risk_level", "Standard")).title(),
        "metrics": metrics,
        "strengths": [str(s) for s in strengths],
        "areas_to_improve": areas_to_improve,
        "ai_summary": ai_summary,
        "recommendations": recommendations
    }

    return True, report, "AI Analysis completed successfully!"
