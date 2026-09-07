"""
CricFit AI — Unified Schema Adapter
===================================
Converts raw model outputs and Groq LLM insights into the unified,
7-metric Biomechanical Report schema consumed by the frontend charts,
report view, and PDF exporter.
"""

import uuid
from datetime import datetime
from typing import Dict, Any


def adapt_to_unified_report(
    activity_type: str,
    raw_model_output: Dict[str, Any],
    llm_insights: Dict[str, Any],
    video_url: str = None,
    pdf_url: str = None,
    report_id: str = None
) -> Dict[str, Any]:
    """
    Transforms model telemetry + LLM outputs into the unified CricFit AI report format.
    """
    activity = str(activity_type).lower()
    report_id = report_id or f"CRIC-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now()

    metrics = _compute_unified_metrics(activity, raw_model_output)
    
    # Calculate overall score as weighted average of metrics
    overall_score = int(round(
        metrics["movement_quality"] * 0.25 +
        metrics["balance"] * 0.15 +
        metrics["lower_body_stability"] * 0.15 +
        metrics["core_stability"] * 0.15 +
        metrics["coordination"] * 0.15 +
        metrics["body_symmetry"] * 0.15
    ))
    overall_score = max(30, min(99, overall_score))

    # Risk level determination
    if overall_score >= 80:
        risk_level = "Low"
    elif overall_score >= 65:
        risk_level = "Moderate"
    else:
        risk_level = "High"

    # Map LLM strengths and areas to improve
    strengths = llm_insights.get("strengths", ["Solid athletic posture and intent."])
    areas_to_improve = llm_insights.get("areas_to_improve", [])
    
    # Standardize areas_to_improve
    formatted_areas = []
    for item in areas_to_improve:
        if isinstance(item, dict):
            formatted_areas.append({
                "area": item.get("area", "Movement Stability"),
                "score": metrics.get("movement_quality", overall_score),
                "priority": item.get("priority", "Medium"),
                "explanation": item.get("impact", item.get("explanation", "Targeted physical optimization."))
            })
        elif isinstance(item, str):
            formatted_areas.append({
                "area": item,
                "score": metrics.get("movement_quality", overall_score),
                "priority": "Medium",
                "explanation": f"Recommended area for conditioning: {item}."
            })

    # Standardize recommendations / exercises
    exercises = llm_insights.get("exercises", [])
    recommendations = []
    for ex in exercises:
        if isinstance(ex, dict):
            recommendations.append({
                "exercise": ex.get("exercise_name", "Conditioning Drill"),
                "target": ex.get("target_area", "Biomechanics"),
                "sets": ex.get("sets_and_reps", "3 sets × 10 reps"),
                "difficulty": ex.get("difficulty", "Intermediate"),
                "reason": ex.get("how_it_improves", "Develops kinetic power and reduces injury risk.")
            })

    report = {
        "id": report_id,
        "activity": activity,
        "timestamp": now.isoformat(),
        "date_str": now.strftime("%d %b %Y, %I:%M %p"),
        "overall_score": overall_score,
        "movement_quality": metrics["movement_quality"],
        "risk_level": risk_level,
        "metrics": metrics,
        "ai_summary": llm_insights.get("plain_language_summary", ""),
        "technique_analysis": llm_insights.get("technique_analysis", ""),
        "strengths": strengths,
        "areas_to_improve": formatted_areas,
        "exercises": exercises,
        "recommendations": recommendations,
        "how_following_improves": llm_insights.get("how_following_improves", ""),
        "nutrition_plan": llm_insights.get("nutrition_plan", {}),
        "annotated_video_url": video_url,
        "pdf_url": pdf_url,
        "raw_model_output": raw_model_output,
    }

    # Attach activity-specific telemetry badges
    if activity == "batting" and "shot_classification" in raw_model_output:
        report["shot_classification"] = raw_model_output["shot_classification"]
    elif activity == "bowling":
        if "arm_classification" in raw_model_output:
            report["arm_classification"] = raw_model_output["arm_classification"]
        if "pace_classification" in raw_model_output:
            report["pace_classification"] = raw_model_output["pace_classification"]
        if "closest_pro_match" in raw_model_output:
            report["closest_pro_match"] = raw_model_output["closest_pro_match"]
    elif activity in ("yoyo", "yoyo_test"):
        if "shuttle_metrics" in raw_model_output:
            report["shuttle_metrics"] = raw_model_output["shuttle_metrics"]
        if "rest_compliance" in raw_model_output:
            report["rest_compliance"] = raw_model_output["rest_compliance"]
        if "level_reference" in raw_model_output:
            report["level_reference"] = raw_model_output["level_reference"]

    return report


def _compute_unified_metrics(activity: str, raw: Dict[str, Any]) -> Dict[str, int]:
    """Extracts and scales the 7 standard biomechanical radar metrics."""
    if activity == "batting":
        comp = raw.get("comparison", {})
        mq = comp.get("movement_quality_similarity_pct", 76.0)
        sym = comp.get("symmetry_score", 78.0)
        
        # Invert deviations to 0-100 scores
        coord_dev = comp.get("coordination_timing_deviation_frames", 3)
        coord_score = max(50, min(95, int(100 - coord_dev * 6)))
        
        mob_dev = comp.get("mobility_indicator_deg_deviation", 8.0)
        mob_score = max(50, min(95, int(100 - mob_dev * 2.5)))
        
        bal_drift = abs(comp.get("balance_indicator", 0.05))
        bal_score = max(50, min(95, int(100 - bal_drift * 300)))
        
        core_var = abs(comp.get("core_stability_indicator", 15.0))
        core_score = max(50, min(95, int(100 - core_var * 1.5)))

        return {
            "balance": int(bal_score),
            "lower_body_stability": int((mob_score + bal_score) // 2),
            "hip_mobility": int(mob_score),
            "core_stability": int(core_score),
            "coordination": int(coord_score),
            "body_symmetry": int(max(40, min(98, sym))),
            "movement_quality": int(max(40, min(98, mq)))
        }

    elif activity == "bowling":
        comp = raw.get("comparison", {})
        mq = comp.get("movement_quality_similarity_pct", 78.0)
        raw_sym = comp.get("symmetry_score", 0.82)
        sym = raw_sym * 100 if raw_sym <= 1.0 else raw_sym
        
        timing_dev = comp.get("coordination_timing_deviation_frames", 2.0)
        coord_score = max(50, min(95, int(100 - timing_dev * 5)))
        
        # Bowling balance & stability derived from movement quality & symmetry
        bal_score = int(mq * 0.95)
        core_score = int((sym + mq) / 2)
        hip_mob = int(min(95, mq + 2))
        lower_stab = int(min(95, sym - 2))

        return {
            "balance": max(45, min(95, bal_score)),
            "lower_body_stability": max(45, min(95, lower_stab)),
            "hip_mobility": max(45, min(95, hip_mob)),
            "core_stability": max(45, min(95, core_score)),
            "coordination": max(45, min(95, coord_score)),
            "body_symmetry": max(45, min(98, int(sym))),
            "movement_quality": max(45, min(98, int(mq)))
        }

    else:  # Yo-Yo Test / Endurance
        shuttle_metrics = raw.get("shuttle_metrics", {})
        shuttles = shuttle_metrics.get("shuttles_detected", 20)
        trend = shuttle_metrics.get("cadence_trend", "stable")
        
        rest_comp = raw.get("rest_compliance", {})
        late_count = rest_comp.get("late_recovery_count", 0)
        
        base_score = min(92, 50 + shuttles * 1.5)
        if trend == "declining":
            base_score -= 6
        elif trend == "increasing":
            base_score += 4
            
        recovery_penalty = min(20, late_count * 4)
        stamina_score = max(40, int(base_score - recovery_penalty))

        return {
            "balance": max(50, min(95, int(stamina_score + 2))),
            "lower_body_stability": max(50, min(95, int(stamina_score - 3))),
            "hip_mobility": max(50, min(95, int(stamina_score - 2))),
            "core_stability": max(50, min(95, int(stamina_score))),
            "coordination": max(50, min(95, int(stamina_score + 4))),
            "body_symmetry": 85,
            "movement_quality": max(45, min(98, stamina_score))
        }
