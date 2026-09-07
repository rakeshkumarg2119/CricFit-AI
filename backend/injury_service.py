"""
CricFit AI — Injury Analysis Service
Pure business logic; no FastAPI / Streamlit dependencies.
"""

RED_FLAG_KEYWORDS = [
    "rapidly worsening",
    "inability to bear weight",
    "deformity",
    "loss of function",
    "significant swelling",
    "new severe numbness",
    "new weakness",
    "loss of bladder",
    "loss of bowel",
    "chest pain",
    "difficulty breathing",
    "fainting",
]

# Duration strings sent by the frontend selectbox
_LONG_DURATIONS = {"1–2 weeks", "More than 2 weeks", "More than 1 month"}
_VERY_LONG_DURATIONS = {"More than 1 month"}


def check_red_flags(symptoms: list, custom_description: str) -> list:
    flags_found = []
    text = (" ".join(symptoms) + " " + custom_description).lower()
    for kw in RED_FLAG_KEYWORDS:
        if kw in text:
            flags_found.append(f"Possible '{kw}' detected — seek prompt medical evaluation.")
    return flags_found


def determine_stage_and_severity(
    pain_intensity: float, duration: str, symptoms: list
) -> tuple:
    """
    Returns (stage: int, severity: str, estimated_recovery: str).
    pain_intensity is a float in [0, 10].
    """
    if pain_intensity >= 7 or len(symptoms) > 5 or duration in _VERY_LONG_DURATIONS:
        return (
            3,
            "Significant",
            "Recovery may take several weeks to months depending on the condition.",
        )
    elif pain_intensity >= 4 or duration in _LONG_DURATIONS:
        return (
            2,
            "Moderate",
            "May require several weeks depending on the underlying issue.",
        )
    else:
        return (1, "Minor", "May improve within a few days with adequate rest.")


def _infer_condition(symptoms: list, custom_description: str) -> str:
    combined = (" ".join(symptoms) + " " + custom_description).lower()
    if "back" in combined:
        return "Possible Lower Back Strain"
    if "shoulder" in combined:
        return "Possible Shoulder Strain"
    if "knee" in combined:
        return "Possible Knee Ligament Sprain"
    if "elbow" in combined:
        return "Possible Elbow Tendinopathy"
    if "ankle" in combined:
        return "Possible Ankle Sprain"
    if "neck" in combined:
        return "Possible Cervical Muscle Strain"
    if "hip" in combined or "groin" in combined:
        return "Possible Hip / Groin Strain"
    if "wrist" in combined or "hand" in combined:
        return "Possible Wrist or Hand Injury"
    return "General Musculoskeletal Strain"


def analyze(
    symptoms: list,
    custom_description: str,
    pain_intensity: float,
    duration: str,
    activity_context: str,
) -> dict:
    """
    Run injury screening and return a structured result dict.
    Always returns a dict with success=True on normal completion.
    """
    red_flags = check_red_flags(symptoms, custom_description)
    stage, severity, est_recovery = determine_stage_and_severity(
        pain_intensity, duration, symptoms
    )

    if red_flags:
        stage = 4
        severity = "HIGH-RISK / URGENT"
        est_recovery = "Requires prompt medical evaluation — do not delay."

    possible_condition = _infer_condition(symptoms, custom_description)

    # Recommendations scale with severity
    recommendations = [
        "Reduce activities that aggravate the pain.",
        "Apply ice (first 48 h) then heat, and elevate if possible.",
        "Allow adequate rest and recovery.",
    ]
    if stage >= 2:
        recommendations.append(
            "Consider evaluation by a qualified healthcare professional."
        )
    if stage >= 3:
        recommendations.append(
            "Avoid pushing through significant pain — further injury is possible."
        )
    if stage == 4:
        recommendations.insert(
            0,
            "🚨 Seek urgent medical evaluation. Do not play through these symptoms.",
        )

    medical_guidance = {
        "doctor_visit": stage >= 2,
        "urgency": (
            "Urgent evaluation"
            if stage == 4
            else "Prompt consultation"
            if stage == 3
            else "Routine consultation"
            if stage == 2
            else "Monitor and self-manage"
        ),
    }

    summary = (
        f"Based on the reported symptoms, the screening suggests a {possible_condition.lower()}. "
        f"Symptoms appear to be occurring {activity_context.lower()}. "
        f"The current severity is assessed as {severity.lower()}. "
        f"{est_recovery}"
    )

    return {
        "success": True,
        "possible_condition": possible_condition,
        "confidence": 0.95 if stage == 4 else 0.82,
        "stage": stage,
        "severity": severity,
        "estimated_recovery": est_recovery,
        "summary": summary,
        "recommendations": recommendations,
        "medical_guidance": medical_guidance,
        "red_flags": red_flags,
    }
