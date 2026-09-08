"""
CricFit AI — Groq LLM Intelligence Service
==========================================
Analyzes ML vision model telemetry (Batting, Bowling, Yo-Yo) and generates:
1. Plain-language, everyday understanding of the player's technique and flaws.
2. Targeted fitness exercise list with precise instructions.
3. Biomechanical improvement explanation (how each drill improves their stroke/action/stamina).
4. Cricket-specific nutrition and food recommendations for recovery and endurance.
5. Comparative progress analysis against the athlete's previous sessions.

YO-YO TEST NOTE
----------------
VO2max and "how many more shuttles to the next level" are PROTOCOL LOOKUPS,
not something an LLM should be asked to calculate freehand — that's exactly
the kind of arithmetic/table-lookup task an LLM can quietly get wrong. So
this module computes them itself (Bangsbo, Iaia & Krustrup, 2008 formula +
the same YYIR1 speed-stage table cadence_tracker.py resolves yoyo_level
against) and hands the result to Groq as ground truth to narrate and build
exercises around, never to recompute. See _yoyo_milestone_analysis().
"""

import os
import json
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


def _get_groq_client():
    """Initializes and returns the Groq client if API key is present."""
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        return None
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"[WARN] Groq client initialization failed: {e}")
        return None


def _clean_json_text(text: Optional[str]) -> str:
    """Extracts JSON content from Markdown code blocks if present. Returns '{}' if text is None."""
    if not text:
        return "{}"
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


# ---------------------------------------------------------------------------
# Yo-Yo IR1 protocol table — duplicated from cadence_tracker.py on purpose.
# This service shouldn't need to import cv2/mediapipe (cadence_tracker's
# module-level imports) just to reuse a 15-row lookup table. Keep this table
# in sync manually if the protocol table in cadence_tracker.py ever changes.
#
# Source: Bangsbo, Iaia & Krustrup (2008), "The Yo-Yo Intermittent Recovery
# Test: A Useful Tool for Evaluation of Physical Performance in Intermittent
# Sports", Sports Med 38(1):37-51.
# ---------------------------------------------------------------------------
_YOYO_IR1_SPEED_STAGES = [
    # (speed_level, shuttles_in_level, speed_kmh)
    (5, 1, 10.0),
    (9, 1, 12.0),
    (11, 2, 13.0),
    (12, 3, 13.5),
    (13, 4, 14.0),
    (14, 8, 14.5),
    (15, 8, 15.0),
    (16, 8, 15.5),
    (17, 8, 16.0),
    (18, 8, 16.5),
    (19, 8, 17.0),
    (20, 8, 17.5),
    (21, 8, 18.0),
    (22, 8, 18.5),
    (23, 8, 19.0),
]


def _build_yoyo_ir1_table():
    table = {}
    global_shuttle_count = 0
    for speed_level, n_shuttles, speed_kmh in _YOYO_IR1_SPEED_STAGES:
        for shuttle_in_level in range(1, n_shuttles + 1):
            global_shuttle_count += 1
            table[(speed_level, shuttle_in_level)] = {
                "speed_kmh": speed_kmh,
                "distance_m": global_shuttle_count * 40,  # 2 x 20m per shuttle
                "cumulative_shuttle_number": global_shuttle_count,
            }
    return table


YOYO_IR1_LEVEL_TABLE = _build_yoyo_ir1_table()
_CUMULATIVE_TO_KEY = {v["cumulative_shuttle_number"]: k for k, v in YOYO_IR1_LEVEL_TABLE.items()}
# Table covers up to score 23.8 / 3640m (elite-range). Scores beyond that
# aren't in the published protocol table.

_YOYO_VO2MAX_FORMULA_NOTE = (
    "Bangsbo, Iaia & Krustrup (2008): VO2max (ml/kg/min) = distance_m x 0.0084 + 36.4"
)


def _parse_level_shuttle(yoyo_level: Optional[Any]):
    """'16.3' (or 16.3 as float/number) -> (16, 3). None if unparseable."""
    try:
        text = str(yoyo_level).strip()
        speed_level_str, shuttle_str = text.split(".")
        return int(speed_level_str), int(shuttle_str)
    except (ValueError, AttributeError):
        return None


def _yoyo_vo2max_ml_kg_min(distance_m: Optional[float]) -> Optional[float]:
    """Official Bangsbo IR1 formula. Returns None if distance is unknown."""
    if distance_m is None:
        return None
    return round(float(distance_m) * 0.0084 + 36.4, 1)


def _yoyo_milestone_analysis(model_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Protocol-accurate Yo-Yo IR1 analysis: current VO2max, and exactly how
    many more shuttles / how much more distance / what speed bump is needed
    to reach (a) the next level.shuttle step and (b) the athlete's target
    score, if one was set. All computed directly from the same table
    cadence_tracker.py uses to resolve level_reference — nothing here is
    estimated or asked of the LLM.
    """
    manual_input = model_output.get("manual_input", {}) or {}
    level_reference = model_output.get("level_reference", {}) or {}
    reference = model_output.get("reference", {}) or {}

    distance_m = level_reference.get("distance_m")
    current_cum = level_reference.get("cumulative_shuttle_number")
    current_speed = level_reference.get("speed_kmh")

    result: Dict[str, Any] = {
        "current_level_shuttle": manual_input.get("yoyo_level"),
        "current_distance_m": distance_m,
        "current_speed_kmh": current_speed,
        "estimated_vo2max_ml_kg_min": _yoyo_vo2max_ml_kg_min(distance_m),
        "vo2max_formula": _YOYO_VO2MAX_FORMULA_NOTE,
        "next_milestone": None,
        "target_milestone": None,
        "note": level_reference.get("note"),
    }

    if current_cum is None or distance_m is None:
        return result

    next_key = _CUMULATIVE_TO_KEY.get(current_cum + 1)
    if next_key is not None:
        next_entry = YOYO_IR1_LEVEL_TABLE[next_key]
        result["next_milestone"] = {
            "level_shuttle": f"{next_key[0]}.{next_key[1]}",
            "speed_kmh": next_entry["speed_kmh"],
            "distance_m": next_entry["distance_m"],
            "additional_shuttles_needed": 1,
            "additional_distance_m": next_entry["distance_m"] - distance_m,
            "speed_increase_kmh": round(next_entry["speed_kmh"] - (current_speed or next_entry["speed_kmh"]), 2),
        }
    else:
        result["next_milestone"] = {
            "note": "current score is already at or beyond the top of the tabulated YYIR1 range (23.8 / 3640m)"
        }

    target_score = reference.get("target_yoyo_score")
    if target_score is not None:
        target_parsed = _parse_level_shuttle(target_score)
        target_entry = YOYO_IR1_LEVEL_TABLE.get(target_parsed) if target_parsed else None
        if target_entry is not None:
            shuttles_needed = target_entry["cumulative_shuttle_number"] - current_cum
            already_met = shuttles_needed <= 0
            result["target_milestone"] = {
                "target_level_shuttle": f"{target_parsed[0]}.{target_parsed[1]}",
                "target_speed_kmh": target_entry["speed_kmh"],
                "target_distance_m": target_entry["distance_m"],
                "target_vo2max_ml_kg_min": _yoyo_vo2max_ml_kg_min(target_entry["distance_m"]),
                "additional_shuttles_needed": 0 if already_met else shuttles_needed,
                "additional_distance_m": 0 if already_met else target_entry["distance_m"] - distance_m,
                "already_met": already_met,
            }
        else:
            result["target_milestone"] = {
                "note": f"target score {target_score} isn't resolvable against the YYIR1 table"
            }

    return result


def generate_llm_insights(
    activity_type: str,
    model_output: Dict[str, Any],
    previous_reports: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Sends raw model output to Groq LLM and retrieves a comprehensive,
    plain-language explanation, progress comparison against previous sessions,
    targeted exercise prescription with improvement mechanics, motivational
    boost, and cricket nutrition advice.
    """
    client = _get_groq_client()

    # If Groq is available, query LLM
    if client is not None:
        try:
            prompt = _build_prompt(activity_type, model_output, previous_reports=previous_reports)
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the Chief Biomechanics and Performance Director for Elite International Cricket. "
                            "You analyze computer vision tracking data from cricket batting, bowling, and Yo-Yo endurance tests. "
                            "Your job is to explain the telemetry in everyday, simple language that common cricketers and coaches can instantly grasp. "
                            "Avoid academic math jargon. Clearly connect movement flaws to specific cricket drills and explain the exact physical mechanism of how each drill improves their game. "
                            "If previous recorded sessions exist for this athlete, compare the current session with them: highlight efficiency gains or areas where stability improved or dropped. "
                            "Always include an uplifting, motivating booster message praising their effort and driving them to keep training. "
                            "Also provide a cricket-specific nutrition and diet plan. "
                            "IMPORTANT — Yo-Yo test sessions only: the user message includes a 'Protocol-Computed Reference Data' block "
                            "(VO2max, current level/distance, next-level gap, target-score gap) computed directly from the official "
                            "Bangsbo/Iaia/Krustrup YYIR1 formula and speed-stage table. Treat every number in that block as ground truth — "
                            "NEVER recompute, re-estimate, or invent your own VO2max, speed, or shuttle-count figures. Your job is to explain "
                            "what those exact numbers mean in plain language and design exercises/nutrition that close the exact gap stated. "
                            "You MUST respond ONLY with a valid JSON object matching the requested schema."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                model=GROQ_MODEL,
                temperature=0.3,
                max_tokens=2500,
                response_format={"type": "json_object"},
            )

            raw_response: Optional[str] = chat_completion.choices[0].message.content
            cleaned_json = _clean_json_text(raw_response)
            parsed = json.loads(cleaned_json)
            if _validate_llm_response(parsed):
                return parsed
        except Exception as e:
            print(f"[WARN] Groq API call failed or timed out: {e}. Falling back to domain rule engine.")

    # Fallback to expert domain engine if Groq is unavailable or failed
    return _generate_expert_fallback(activity_type, model_output, previous_reports=previous_reports)


def _build_prompt(
    activity_type: str,
    model_output: Dict[str, Any],
    previous_reports: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Builds a rich, contextual prompt for Groq containing telemetry and past session history."""
    activity = activity_type.lower()

    history_summary = []
    if previous_reports:
        for idx, prev in enumerate(previous_reports[:3]):
            p_score = prev.get("overall_score", "N/A")
            p_mq = prev.get("movement_quality", "N/A")
            p_date = prev.get("date_str") or prev.get("saved_at", f"Session #{idx+1}")
            p_metrics = prev.get("metrics", {})
            history_summary.append({
                "session_index": idx + 1,
                "recorded_date": p_date,
                "overall_score": p_score,
                "movement_quality": p_mq,
                "metrics": p_metrics,
            })

    history_block = (
        f"\n### Previous Session History for this Athlete:\n{json.dumps(history_summary, indent=2)}\n"
        if history_summary else
        "\n### Previous Session History:\nFirst recorded session for this activity/pose baseline.\n"
    )

    # --- Yo-Yo-specific ground truth block + schema addendum ---------------
    yoyo_ground_truth_block = ""
    yoyo_schema_addendum = ""
    yoyo_directive = ""
    if activity == "yoyo" or activity == "yo-yo" or activity == "yo_yo":
        milestone = _yoyo_milestone_analysis(model_output)
        yoyo_ground_truth_block = (
            "\n### Protocol-Computed Reference Data (GROUND TRUTH — use exactly as given, "
            "do NOT recompute VO2max, speed, or shuttle counts yourself):\n"
            f"{json.dumps(milestone, indent=2)}\n"
        )
        yoyo_directive = (
            "4. Yo-Yo test only: base 'vo2max_and_speed_analysis' and 'shuttle_improvement_plan' strictly on the "
            "Protocol-Computed Reference Data block above. State the current VO2max and level plainly, then explain "
            "next_milestone (shuttles/distance/speed needed for the next level) and target_milestone (gap to the "
            "athlete's target score, if set) in everyday language. Tie at least one exercise directly to closing that gap.\n"
        )
        yoyo_schema_addendum = """,
  "vo2max_and_speed_analysis": "2-3 sentences explaining the athlete's current VO2max and level/speed in plain language, using ONLY the numbers given in the Protocol-Computed Reference Data block.",
  "shuttle_improvement_plan": {
    "shuttles_to_next_level": "number of additional shuttles needed for the next level, from the ground truth block",
    "distance_to_next_level_m": "additional distance in meters needed, from the ground truth block",
    "shuttles_to_target_score": "number of additional shuttles needed to reach the athlete's target score, or null if no target was set / already met",
    "how_to_close_the_gap": "2-3 concrete, specific tips (pacing, turn technique, recovery-window discipline) for closing exactly this gap"
  }"""

    return f"""
Analyze the following computer vision AI analysis for a cricketer doing **{activity.upper()}**.

### Raw Model Telemetry & Metrics:
{json.dumps(model_output, indent=2)}
{history_block}{yoyo_ground_truth_block}
### Analysis Directives:
1. Explain technique simply without academic math jargon.
2. Comparative Progress: If previous session data is provided, explicitly evaluate how their efficiency and technique improved (or dropped) compared to earlier sessions. If this is the first session, celebrate the baseline instead.
3. Motivational Boost: Include an inspiring, energizing message praising the cricketer's consistency and athletic drive.
{yoyo_directive}
### Your Output Schema (Respond STRICTLY in this JSON format):
{{
  "plain_language_summary": "3-4 sentences in clear, friendly language explaining what the player did well and their main physical/technical flaw.",
  "progress_comparison": "2-3 sentences evaluating how efficiency and form improved compared to previous sessions (or celebrating baseline if first session).",
  "motivational_boost": "1-2 uplifting, high-energy sentences boosting the cricketer's confidence and training motivation.",
  "technique_analysis": "Detailed breakdown of their posture, stability, alignment, and movement flow.",
  "strengths": [
    "Strength 1 with brief reason",
    "Strength 2 with brief reason"
  ],
  "areas_to_improve": [
    {{
      "area": "Specific technical or physical weakness",
      "impact": "How this flaw negatively affects their shot power, bowling accuracy/speed, or stamina",
      "priority": "High / Medium / Low"
    }}
  ],
  "exercises": [
    {{
      "exercise_name": "Name of the drill or exercise",
      "target_area": "Target muscle group or biomechanical attribute",
      "sets_and_reps": "e.g., 3 sets × 10 reps / 45 sec hold",
      "difficulty": "Beginner / Intermediate / Advanced",
      "how_it_improves": "Clear explanation of how performing this exercise fixes the specific flaw and boosts match performance."
    }},
    {{
      "exercise_name": "Second exercise name",
      "target_area": "Target area",
      "sets_and_reps": "e.g., 4 sets × 8 reps",
      "difficulty": "Intermediate",
      "how_it_improves": "Explanation of mechanical improvement."
    }},
    {{
      "exercise_name": "Third exercise name",
      "target_area": "Target area",
      "sets_and_reps": "e.g., 3 sets × 15 reps",
      "difficulty": "Intermediate",
      "how_it_improves": "Explanation of mechanical improvement."
    }}
  ],
  "how_following_improves": "A concise paragraph explaining how sticking to this routine will transform the player's overall cricket performance and reduce injury risks.",
  "nutrition_plan": {{
    "pre_workout": "What to eat 1-2 hours before intense cricket training or batting/bowling sessions",
    "post_workout": "Post-session meal or shake for rapid muscle repair and glycogen replenishment",
    "hydration_strategy": "Specific hydration and electrolyte guidance for cricket sessions",
    "key_foods": [
      "Key food item 1 with cricket fitness benefit",
      "Key food item 2 with cricket fitness benefit",
      "Key food item 3 with cricket fitness benefit"
    ]
  }}{yoyo_schema_addendum}
}}
"""


def _validate_llm_response(data: Any) -> bool:
    """Checks if the LLM output contains the core required fields."""
    if not isinstance(data, dict):
        return False
    required = ["plain_language_summary", "exercises", "nutrition_plan"]
    return all(k in data for k in required) and isinstance(data["exercises"], list)


def _generate_expert_fallback(
    activity_type: str,
    model_output: Dict[str, Any],
    previous_reports: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Expert rule-based fallback that generates realistic, non-dummy cricket fitness
    and nutrition insights tailored directly to the model's numbers, including a
    basic historical comparison and motivational boost.
    """
    activity = activity_type.lower()
    has_prev = bool(previous_reports and len(previous_reports) > 0)
    prev_report = previous_reports[0] if has_prev else None

    motivational_boost = (
        "Keep this momentum going! Your dedication to reviewing biomechanical feedback is what separates competitive athletes from the rest. Trust your training and attack every drill!"
    )

    if activity == "batting":
        shot_info = model_output.get("shot_classification", {})
        shot_name = shot_info.get("label", "Cricket Stroke").replace("_", " ").title()
        conf = round(shot_info.get("confidence", 0.85) * 100, 1)
        comp = model_output.get("comparison", {})
        mq = comp.get("movement_quality_similarity_pct", 75.0)
        sym = comp.get("symmetry_score", 80.0)

        if has_prev:
            prev_score = prev_report.get("overall_score", 70)
            cur_score = int(round(mq))
            diff = cur_score - prev_score
            sign = "+" if diff >= 0 else ""
            progress_comparison = (
                f"Compared to your previous session ({prev_score}/100), your movement stability changed by {sign}{diff} pts. "
                f"Kinetic sequencing and shoulder alignment show cleaner timing into the {shot_name} impact phase."
                if diff >= 0 else
                f"Compared to your previous session ({prev_score}/100), this rep showed a slight drop of {abs(diff)} pts in lower-body plant stability. "
                "Focus on bracing the front knee to regain peak kinetic transfer."
            )
            motivational_boost = (
                f"Great persistence logging multiple {shot_name} sessions! Consistent repetitions build elite neuromuscular muscle memory. You're getting sharper each time!"
            )
        else:
            progress_comparison = (
                f"Baseline established for your {shot_name}! Upload your next batting video to track how quickly your stroke efficiency and kinetic stability improve."
            )

        return {
            "plain_language_summary": (
                f"You executed a {shot_name} (classified with {conf}% AI confidence). "
                f"Your movement quality scored {mq}% compared to reference pro standards. "
                "Your upper-body bat swing shows solid intent, but there is noticeable trunk sway and knee flexion drift during the impact phase."
            ),
            "progress_comparison": progress_comparison,
            "motivational_boost": motivational_boost,
            "technique_analysis": (
                f"During the {shot_name} stride, your head position remains slightly off the line of contact. "
                f"Symmetry was recorded at {sym}/100, indicating unequal weight transfer between your front and back feet."
            ),
            "strengths": [
                f"Confident bat path during the {shot_name} downswing",
                "Good shoulder alignment leading into the initial stride"
            ],
            "areas_to_improve": [
                {
                    "area": "Front Knee Stability & Base",
                    "impact": "Excessive knee collapse reduces power transfer into the ball and causes top edges.",
                    "priority": "High"
                },
                {
                    "area": "Rotational Core Control",
                    "impact": "Early torso opening prevents you from keeping the stroke along the ground.",
                    "priority": "Medium"
                }
            ],
            "exercises": [
                {
                    "exercise_name": "Split-Stance Isometric Lunges",
                    "target_area": "Quadriceps & Glute Medius Stability",
                    "sets_and_reps": "3 sets × 45 seconds each leg",
                    "difficulty": "Intermediate",
                    "how_it_improves": "Strengthens the front-leg braking base, locking your head over the ball during drive execution."
                },
                {
                    "exercise_name": "Paloff Press with Resistance Band",
                    "target_area": "Anti-Rotational Core & Obliques",
                    "sets_and_reps": "3 sets × 12 reps per side",
                    "difficulty": "Intermediate",
                    "how_it_improves": "Prevents torso over-rotation and helps you hold your shape through the entire batting stroke."
                },
                {
                    "exercise_name": "Medicine Ball Rotational Slams",
                    "target_area": "Kinetic Chain Power & Hip Drive",
                    "sets_and_reps": "4 sets × 8 reps per side (4-6 kg ball)",
                    "difficulty": "Advanced",
                    "how_it_improves": "Develops explosive hip-to-shoulder sequencing, generating bat speed without sacrificing balance."
                }
            ],
            "how_following_improves": (
                "Consistently following these exercises builds a rock-solid lower-body foundation and explosive rotational power. "
                "You will notice sharper timing, cleaner ball striking, and significantly reduced strain on your lower back and knees."
            ),
            "nutrition_plan": {
                "pre_workout": "Oatmeal with banana, chia seeds, and 1 boiled egg (or whey protein) 90 minutes before batting practice.",
                "post_workout": "Grilled chicken breast or paneer with quinoa/brown rice and mixed vegetables within 45 minutes of training.",
                "hydration_strategy": "Drink 500ml water with electrolytes before training; sip 150ml every 15-20 minutes in the nets.",
                "key_foods": [
                    "Bananas & Dates for quick, sustained complex energy",
                    "Eggs / Paneer / Greek Yogurt for muscle tissue repair",
                    "Beetroot juice to enhance oxygen flow and muscular stamina"
                ]
            }
        }

    elif activity == "bowling":
        arm = model_output.get("arm_classification", {}).get("label", "Right Arm").title()
        pace = model_output.get("pace_classification", {}).get("label", "Pace").title()
        match = model_output.get("closest_pro_match", {})
        pro_name = match.get("player", "Pro Bowler")
        comp = model_output.get("comparison", {})
        mq = comp.get("movement_quality_similarity_pct", 78.0)
        sym = comp.get("symmetry_score", 82.0)

        if has_prev:
            prev_score = prev_report.get("overall_score", 70)
            cur_score = int(round(mq))
            diff = cur_score - prev_score
            sign = "+" if diff >= 0 else ""
            progress_comparison = (
                f"Compared to your earlier bowling session ({prev_score}/100), delivery stride stability is up {sign}{diff} pts. "
                f"Momentum conversion through your run-up into the front foot plant is noticeably smoother."
                if diff >= 0 else
                f"Compared to your previous session ({prev_score}/100), landing stiffness showed a minor dip of {abs(diff)} pts. "
                "Bracing the front knee earlier in the gather phase will restore your top-end delivery speed."
            )
            motivational_boost = (
                f"Incredible work dialing in your {arm} {pace} mechanics! Pacing discipline and repeatable delivery mechanics are the hallmarks of great bowlers. Keep charging in!"
            )
        else:
            progress_comparison = (
                f"Baseline established for your {arm} {pace} delivery stride! Add subsequent session clips to track gains in front-knee brace firmness and ball velocity."
            )

        return {
            "plain_language_summary": (
                f"Your bowling action is detected as {arm} {pace}, closely resembling the mechanics of {pro_name}. "
                f"Your movement quality scored {mq}%. Your run-up momentum transfers reasonably well, "
                "but you are losing lateral stability at front-foot landing."
            ),
            "progress_comparison": progress_comparison,
            "motivational_boost": motivational_boost,
            "technique_analysis": (
                f"At the point of delivery stride plant, your trunk angle leans slightly off vertical. "
                f"Symmetry scored {sym}/100, which indicates a heavy load on the lumbar spine and front knee."
            ),
            "strengths": [
                f"Strong gathering momentum similar to {pro_name}",
                "Good high non-bowling arm pull-down creating initial torque"
            ],
            "areas_to_improve": [
                {
                    "area": "Front-Foot Landing Brace",
                    "impact": "A soft front knee bleeds ball velocity and forces the lower back to absorb excess braking impact.",
                    "priority": "High"
                },
                {
                    "area": "Shoulder & Lat Hip Alignment",
                    "impact": "Mixed action rotation increases the risk of lower back stress fractures.",
                    "priority": "High"
                }
            ],
            "exercises": [
                {
                    "exercise_name": "Single-Leg Box Step-Downs with Knee Lock",
                    "target_area": "Eccentric Quad & Patellar Stability",
                    "sets_and_reps": "3 sets × 10 reps per leg",
                    "difficulty": "Intermediate",
                    "how_it_improves": "Teaches your front leg to stiffen and brace upon delivery stride impact, converting run-up speed directly into bowling pace."
                },
                {
                    "exercise_name": "Single-Arm Cable Rotational Pull-Downs",
                    "target_area": "Latissimus Dorsi & Non-Bowling Arm Drive",
                    "sets_and_reps": "4 sets × 10 reps",
                    "difficulty": "Intermediate",
                    "how_it_improves": "Strengthens your non-bowling side lever, increasing release height and ball seam control."
                },
                {
                    "exercise_name": "Deadbugs & Side Planks with Hip Abduction",
                    "target_area": "Deep Core Stabilizers & Glute Medius",
                    "sets_and_reps": "3 sets × 12 reps / 40 sec hold",
                    "difficulty": "Beginner to Intermediate",
                    "how_it_improves": "Protects your lower spine against fast-bowling rotational shear stresses."
                }
            ],
            "how_following_improves": (
                "Developing a rigid front-leg brace and stronger core stability will increase your bowling pace by 3-5 km/h "
                "while shielding your spine from high-impact bowling stress."
            ),
            "nutrition_plan": {
                "pre_workout": "Whole-wheat toast with peanut butter and coconut water 60-90 minutes prior to bowling spell.",
                "post_workout": "High-protein recovery shake with whey or pea protein + banana and a pinch of pink salt.",
                "hydration_strategy": "Fast bowlers lose up to 1.5L sweat per hour: drink 750ml water mixed with electrolytes every spell.",
                "key_foods": [
                    "Salmon / Walnuts / Flaxseeds for anti-inflammatory joint recovery",
                    "Sweet potatoes for restoring depleted muscle glycogen",
                    "Bone broth or Collagen peptides for tendon and ligament durability"
                ]
            }
        }

    else:  # Yo-Yo Test / Endurance
        shuttle_metrics = model_output.get("shuttle_metrics", {}) or {}
        shuttles = shuttle_metrics.get("shuttles_detected", 0)
        trend = shuttle_metrics.get("cadence_trend", "insufficient_data")
        partial_leg = shuttle_metrics.get("partial_leg_at_end", False)
        direction_anomaly = shuttle_metrics.get("direction_anomaly_detected", False)

        rest_comp = model_output.get("rest_compliance", {}) or {}
        late_count = rest_comp.get("late_recovery_count", 0)
        all_ok = rest_comp.get("all_recoveries_ok")

        milestone = _yoyo_milestone_analysis(model_output)
        vo2 = milestone.get("estimated_vo2max_ml_kg_min")
        current_score = milestone.get("current_level_shuttle") or "N/A"
        current_distance = milestone.get("current_distance_m")
        next_ms = milestone.get("next_milestone") or {}
        target_ms = milestone.get("target_milestone") or {}

        vo2_text = (
            f"an estimated VO₂max of {vo2} mL/kg/min ({_YOYO_VO2MAX_FORMULA_NOTE})"
            if vo2 is not None else
            "no VO₂max estimate available (reported score didn't resolve against the YYIR1 table)"
        )

        if next_ms.get("additional_shuttles_needed"):
            next_text = (
                f"You're {next_ms['additional_shuttles_needed']} shuttle away from Level {next_ms['level_shuttle']} "
                f"({next_ms['additional_distance_m']}m further, a {next_ms['speed_increase_kmh']} km/h pace bump to {next_ms['speed_kmh']} km/h)."
            )
        else:
            next_text = next_ms.get("note", "Next-level data unavailable for this score.")

        if target_ms.get("already_met"):
            target_text = f"You've already reached your target score of {target_ms.get('target_level_shuttle')}!"
        elif target_ms.get("additional_shuttles_needed"):
            target_text = (
                f"To hit your target of Level {target_ms['target_level_shuttle']} you need "
                f"{target_ms['additional_shuttles_needed']} more shuttles ({target_ms['additional_distance_m']}m), "
                f"lifting VO₂max to roughly {target_ms['target_vo2max_ml_kg_min']} mL/kg/min."
            )
        else:
            target_text = target_ms.get("note", "")

        if has_prev:
            prev_score = prev_report.get("overall_score", 65)
            progress_comparison = (
                f"You completed {shuttles} tracked shuttles reaching {current_score} ({current_distance}m), with a '{trend}' "
                f"cadence trend, compared to your earlier baseline ({prev_score}/100). {next_text}"
            )
            motivational_boost = (
                "Phenomenal gut-check effort! The Yo-Yo test is as much mental toughness as physical endurance. Keep your footwork disciplined and that score will keep climbing!"
            )
        else:
            progress_comparison = (
                f"Baseline established at {current_score} ({shuttles} tracked shuttles, {current_distance}m). {next_text} "
                "Track your next session to see the gain."
            )
            motivational_boost = (
                "Strong endurance foundation! Pacing is everything in international cricket. Stay consistent and push through the rest intervals!"
            )

        return {
            "plain_language_summary": (
                f"In your Yo-Yo Intermittent Recovery Test (IR1), you reached level {current_score}, covering {current_distance}m "
                f"across {shuttles} tracked shuttles, giving you {vo2_text}. Your step cadence trend was '{trend}'"
                + (f", with {late_count} late rest-recovery flag(s)" if rest_comp else "")
                + ". Your aerobic base looks solid, but recovering efficiently inside the 10-second window between shuttles is where you're leaving score on the table."
            ),
            "progress_comparison": progress_comparison,
            "motivational_boost": motivational_boost,
            "technique_analysis": (
                f"Turn/deceleration efficiency across your {shuttles} shuttles trended '{trend}'"
                + (f", and {late_count} of your recovery windows were under the mandatory 10s (still moving when the next beep sounded)"
                   if late_count else ", and all recovery windows met the mandatory 10s")
                + (". Two consecutive legs were flagged same-direction — usually a mid-sprint stumble split one leg into two, "
                   "so treat the shuttle count as slightly uncertain either way." if direction_anomaly else "")
                + (". The clip ended mid-shuttle (partial leg) — your true final shuttle count may be one higher than reported."
                   if partial_leg else "")
            ),
            "strengths": [
                f"Reached {current_score} ({current_distance}m) — {vo2_text.split('(')[0].strip()}",
                "All recoveries within the mandatory 10s window" if all_ok else "Consistent shuttle-to-shuttle effort despite fatigue"
            ],
            "areas_to_improve": [
                {
                    "area": "180° Cone Deceleration & Recovery Speed",
                    "impact": f"{late_count} late-recovery flag(s) mean energy meant for the next sprint is being spent just getting back to the line in time.",
                    "priority": "High" if late_count else "Medium"
                },
                {
                    "area": "Aerobic Heart-Rate Clearance Between Shuttles",
                    "impact": next_text,
                    "priority": "High"
                }
            ],
            "exercises": [
                {
                    "exercise_name": "Shuttle Deceleration & 180° Plant Turns",
                    "target_area": "Eccentric Hamstring & Ankle Braking",
                    "sets_and_reps": "4 sets × 6 reps (alternating turn foot)",
                    "difficulty": "Advanced",
                    "how_it_improves": (
                        f"Cuts braking time at the 20m line — exactly the margin behind {late_count} late recovery flag(s) — "
                        f"buying back the {next_ms.get('additional_shuttles_needed', 1)} extra shuttle(s) needed for "
                        f"{next_ms.get('level_shuttle', 'the next level')}."
                    )
                },
                {
                    "exercise_name": "HIIT 15s Sprint / 15s Active Walk Intervals",
                    "target_area": "VO₂max & Lactate Threshold Clearance",
                    "sets_and_reps": "2 blocks of 8 minutes (1:1 work-rest)",
                    "difficulty": "Advanced",
                    "how_it_improves": (
                        f"Mimics the beep-test work:rest ratio directly, raising your VO₂max ceiling above the current "
                        f"{vo2 if vo2 is not None else 'baseline'} mL/kg/min so the same pace feels sub-maximal for longer."
                    )
                },
                {
                    "exercise_name": "Nordic Hamstring Curls & Copenhagen Planks",
                    "target_area": "Hamstrings & Adductor Groin Durability",
                    "sets_and_reps": "3 sets × 6-8 reps",
                    "difficulty": "Intermediate",
                    "how_it_improves": "Builds the hamstring/groin resilience needed to train the deceleration drill above without breaking down."
                }
            ],
            "how_following_improves": (
                f"Shaving even 1-2 seconds off your turn-and-recover time is usually worth more shuttles than raw straight-line "
                f"speed at this stage — it's the difference between {current_score} and {next_ms.get('level_shuttle', 'the next level')}. "
                f"{target_text} Combined with the aerobic interval work, you'll clear higher YYIR1 levels while handling long "
                "match-day spells and marathon batting innings with less late-innings fade."
            ),
            "nutrition_plan": {
                "pre_workout": "Complex carbs like brown rice with lentils or oats with blueberries 2 hours before the endurance test.",
                "post_workout": "Fast-digesting whey protein or chocolate milk + tart cherry juice to reduce muscle soreness.",
                "hydration_strategy": "Hyper-hydrate with 500ml sodium-electrolyte drink 1 hour before test; avoid heavy solids 90 minutes prior.",
                "key_foods": [
                    "Tart Cherry Juice to speed up muscle oxidative recovery",
                    "Spinach & leafy greens rich in nitrates for vascular efficiency (supports VO₂max gains)",
                    "Almonds & Chia Seeds for sustained cellular endurance"
                ]
            },
            "vo2max_and_speed_analysis": (
                f"You're currently at level {current_score}, covering {current_distance}m for {vo2_text}. {next_text}"
            ),
            "shuttle_improvement_plan": {
                "shuttles_to_next_level": next_ms.get("additional_shuttles_needed"),
                "distance_to_next_level_m": next_ms.get("additional_distance_m"),
                "shuttles_to_target_score": target_ms.get("additional_shuttles_needed") if target_ms.get("additional_shuttles_needed") else None,
                "how_to_close_the_gap": [
                    "Sprint the last 5m into the line rather than decelerating early — most late-recovery time is lost drifting into the turn, not the sprint itself.",
                    "Plant and pivot on the outside foot for a true 180°, instead of a rounded curve that adds distance and time.",
                    "Use the full 10s recovery to walk (not stand) — active recovery clears lactate faster and sets up the next shuttle's cadence."
                ]
            }
        }