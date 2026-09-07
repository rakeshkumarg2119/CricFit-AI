import streamlit as st
import time
from config import PAGES
from utils.session import navigate_to
from services.injury_api import analyze_injury, check_backend_health

# Symptom categories based on the user's requirements
SYMPTOM_CATEGORIES = {
    "Pain / Discomfort": [
        "Shoulder pain", "Elbow pain", "Wrist pain", "Hand pain",
        "Lower back pain", "Upper back pain", "Neck pain",
        "Hip pain", "Groin pain", "Knee pain", "Ankle pain", "Foot pain"
    ],
    "Movement-related symptoms": [
        "Difficulty moving", "Reduced range of motion", "Joint stiffness",
        "Muscle tightness", "Weakness", "Reduced balance",
        "Difficulty running", "Difficulty jumping", "Difficulty rotating the body"
    ],
    "Other symptoms": [
        "Swelling", "Bruising", "Tenderness", "Muscle soreness",
        "Numbness / tingling", "Instability", "Pain during batting",
        "Pain during bowling", "Pain during running"
    ]
}

def render_injury_detection_page():
    """Render Injury Detection screening page with Back to Home navigation."""

    # ── Back to Home ──────────────────────────────────────────────────────────
    if st.button("← Back to Home", key="btn_injury_back_home", type="secondary"):
        navigate_to(PAGES["HOME"])

    st.html("""
<div style="margin-bottom: 24px;">
    <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
        🩺 Injury Detection
    </h1>
    <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
        Tell us about your symptoms so CricFit AI can screen for possible injury concerns.
    </p>
</div>
""")

    st.warning("This tool provides preliminary screening information based on the symptoms you provide. It is not a medical diagnosis. If symptoms are severe, worsening, or concerning, consult a qualified healthcare professional.", icon="⚠️")

    # If we already have a result, show the report instead of the form
    if "injury_result" in st.session_state and st.session_state.injury_result is not None:
        render_injury_report(st.session_state.injury_result)
        if st.button("← Back to Symptoms", type="secondary"):
            st.session_state.injury_result = None
            st.rerun()
        return

    st.markdown("### SELECT YOUR SYMPTOMS")
    
    selected_symptoms = []
    
    # Render grouped multi-selects to keep it clean
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pain_symptoms = st.multiselect("Pain / Discomfort", SYMPTOM_CATEGORIES["Pain / Discomfort"])
        selected_symptoms.extend(pain_symptoms)
        
    with col2:
        movement_symptoms = st.multiselect("Movement-related", SYMPTOM_CATEGORIES["Movement-related symptoms"])
        selected_symptoms.extend(movement_symptoms)
        
    with col3:
        other_symptoms = st.multiselect("Other symptoms", SYMPTOM_CATEGORIES["Other symptoms"])
        selected_symptoms.extend(other_symptoms)

    st.markdown("### DESCRIBE YOUR SYMPTOMS")
    custom_description = st.text_area(
        "Additional Information", 
        placeholder="Describe anything else you are experiencing (e.g., 'Pain in my lower back after bowling and discomfort when bending forward.')",
        height=100
    )

    st.markdown("### OPTIONAL ADDITIONAL INFORMATION")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        pain_display = ["0 — No pain", "1–3 — Mild", "4–6 — Moderate", "7–8 — Severe", "9–10 — Very severe"]
        pain_val_map = {"0 — No pain": 0, "1–3 — Mild": 2, "4–6 — Moderate": 5, "7–8 — Severe": 7.5, "9–10 — Very severe": 9.5}
        selected_pain_str = st.selectbox("Pain intensity", pain_display, index=0)
        pain_intensity = pain_val_map[selected_pain_str or "0 — No pain"]

    with c2:
        duration_options = [
            "Less than 1 day",
            "1–3 days",
            "Less than 1 week",
            "1–2 weeks",
            "More than 2 weeks",
            "More than 1 month"
        ]
        duration = st.selectbox("Duration", duration_options)

    with c3:
        context_options = [
            "During batting",
            "During bowling",
            "During running",
            "During training",
            "During rest",
            "After training",
            "Other"
        ]
        activity_context = st.selectbox("When does it occur?", context_options)

    st.html("<br>")

    if st.button("ANALYZE SYMPTOMS", type="primary", use_container_width=True):
        if not selected_symptoms and not custom_description.strip():
            st.error("Please select at least one symptom or describe your symptoms before continuing.")
        else:
            with st.spinner("Analyzing symptoms — please wait..."):
                user_id = st.session_state.get("user", {}).get("_id", "anonymous")
                success, data, msg = analyze_injury(
                    user_id=user_id,
                    symptoms=selected_symptoms,
                    custom_description=custom_description,
                    pain_intensity=float(pain_intensity),
                    duration=duration or "Less than 1 day",
                    activity_context=activity_context or "Other",
                )

                if success:
                    st.session_state.injury_result = data
                    st.session_state.injury_error = None
                    st.rerun()
                else:
                    st.session_state.injury_error = msg

    # Show persistent error with TRY AGAIN button
    if st.session_state.get("injury_error"):
        st.error(st.session_state.injury_error)
        col_err1, col_err2 = st.columns([1, 5])
        with col_err1:
            if st.button("🔄 TRY AGAIN", type="secondary"):
                st.session_state.injury_error = None
                # Check if backend is reachable and hint the user
                if not check_backend_health():
                    st.warning(
                        "⚠️ The FastAPI backend does not appear to be running. "
                        "Start it with: **`uvicorn backend.main:app --reload`** "
                        "from the project root, then click TRY AGAIN.",
                        icon="🖥️",
                    )
                st.rerun()

def render_injury_report(data):
    """Render the structured injury report using st.html() to avoid Markdown parser escaping."""

    # ── Header card: Activity Context / Symptoms / Duration ──────────────────
    activity_context = data.get("activity_context", "Not specified")
    symptoms_str = (
        ", ".join(data.get("symptoms", []))
        if data.get("symptoms")
        else "Custom description only"
    )
    duration = data.get("duration", "—")

    st.html(f"""
<div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1);
            padding: 24px; border-radius: 16px; margin-bottom: 24px;">
    <p style="color: #94A3B8; font-size: 0.85rem; font-weight: 700; margin: 0;
              letter-spacing: 1px;">CRICFIT AI</p>
    <h2 style="color: #FFFFFF; font-size: 1.8rem; margin: 4px 0 16px 0;">INJURY SCREENING REPORT</h2>
    <div style="display: flex; flex-wrap: wrap; gap: 20px;">
        <div>
            <span style="color: #64748B; font-size: 0.8rem; display: block; margin-bottom: 4px;">
                Activity Context
            </span>
            <span style="color: #E2E8F0; font-size: 1rem; font-weight: 600;">
                {activity_context}
            </span>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem; display: block; margin-bottom: 4px;">
                Symptoms Reported
            </span>
            <span style="color: #E2E8F0; font-size: 1rem; font-weight: 600;">
                {symptoms_str}
            </span>
        </div>
        <div>
            <span style="color: #64748B; font-size: 0.8rem; display: block; margin-bottom: 4px;">
                Duration
            </span>
            <span style="color: #E2E8F0; font-size: 1rem; font-weight: 600;">
                {duration}
            </span>
        </div>
    </div>
</div>
""")

    # ── Red flags ─────────────────────────────────────────────────────────────
    red_flags = data.get("red_flags", [])
    if red_flags:
        st.error("🚨 **Your symptoms may require prompt medical evaluation.**\n\n" + "\n".join([f"- {r}" for r in red_flags]))

    # ── Possible Condition / Screening Confidence card ────────────────────────
    confidence = data.get("confidence", 0)
    conf_str = f"Screening Confidence: {int(confidence * 100)}%" if confidence else ""
    possible_condition = data.get("possible_condition", "Unknown")

    st.html(f"""
<div style="background: linear-gradient(145deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95));
            border: 1px solid rgba(239,68,68,0.3); padding: 32px; border-radius: 20px;
            text-align: center; margin-bottom: 24px;">
    <p style="color: #94A3B8; font-size: 0.9rem; font-weight: 700; letter-spacing: 1px;
              margin: 0 0 8px 0;">POSSIBLE INJURY / CONDITION</p>
    <h2 style="color: #F8FAFC; font-size: 2.5rem; font-weight: 800; margin: 0 0 12px 0;">
        {possible_condition}
    </h2>
    <p style="color: #EF4444; font-size: 1rem; font-weight: 600; margin: 0;">{conf_str}</p>
</div>
""")

    # ── Stage + Medical Guidance (two columns using st.columns) ───────────────
    col1, col2 = st.columns(2, gap="large")

    with col1:
        stage = data.get("stage", 1)
        severity = data.get("severity", "Minor")
        est_recovery = data.get("estimated_recovery", "Unknown")

        colors = {
            1: "#10B981",   # Green
            2: "#F59E0B",   # Yellow/Orange
            3: "#F97316",   # Orange
            4: "#EF4444"    # Red
        }
        stage_color = colors.get(stage, "#94A3B8")

        st.html(f"""
<div style="background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.05);
            padding: 24px; border-radius: 16px; height: 100%;">
    <h4 style="color: #F8FAFC; margin: 0 0 16px 0; font-size: 1.1rem; font-weight: 700;">
        SCREENING STAGE
    </h4>
    <div style="display: flex; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 12px;">
        <div style="background: {stage_color}20; color: {stage_color}; font-size: 1.5rem;
                    font-weight: 900; padding: 8px 16px; border-radius: 12px;
                    border: 1px solid {stage_color}50; margin-right: 16px;">
            STAGE {stage}
        </div>
        <span style="color: #E2E8F0; font-size: 1.2rem; font-weight: 700;">{severity} Concern</span>
    </div>
    <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.5; margin: 0;">
        <strong>Estimated recovery:</strong> {est_recovery}
    </p>
</div>
""")

    with col2:
        medical = data.get("medical_guidance", {})
        doctor_visit_text = "Recommended" if medical.get("doctor_visit") else "Not immediately indicated"
        urgency_text = medical.get("urgency", "Monitor")

        st.html(f"""
<div style="background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.05);
            padding: 24px; border-radius: 16px; height: 100%;">
    <h4 style="color: #F8FAFC; margin: 0 0 16px 0; font-size: 1.1rem; font-weight: 700;">
        MEDICAL GUIDANCE
    </h4>
    <div style="margin-bottom: 12px;">
        <span style="color: #94A3B8; font-size: 0.9rem;">Doctor Visit:</span>
        <strong style="color: #E2E8F0; font-size: 1rem; margin-left: 8px;">{doctor_visit_text}</strong>
    </div>
    <div style="margin-bottom: 16px;">
        <span style="color: #94A3B8; font-size: 0.9rem;">Urgency:</span>
        <strong style="color: #E2E8F0; font-size: 1rem; margin-left: 8px;">{urgency_text}</strong>
    </div>
    <p style="color: #94A3B8; font-size: 0.9rem; line-height: 1.5; margin: 0;
              background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px;">
        Consider consulting a qualified sports physician, physiotherapist, or other
        appropriate healthcare professional.
    </p>
</div>
""")

    st.html("<br>")

    # ── AI Screening Insight ──────────────────────────────────────────────────
    summary = data.get("summary", "")

    st.html(f"""
<div style="background: rgba(6,182,212,0.05); border-left: 4px solid #06B6D4;
            padding: 20px; border-radius: 0 12px 12px 0; margin-bottom: 24px;">
    <h4 style="color: #06B6D4; margin: 0 0 8px 0; font-size: 1.05rem;">
        🤖 CRICFIT AI SCREENING INSIGHT
    </h4>
    <p style="color: #E2E8F0; font-size: 1rem; line-height: 1.6; margin: 0;">
        {summary}
    </p>
</div>
""")

    # ── Recommendations ───────────────────────────────────────────────────────
    recs = data.get("recommendations", [])
    if recs:
        st.markdown("### WHAT YOU SHOULD DO")
        for rec in recs:
            st.markdown(f"- {rec}")

    # ── MongoDB save status (non-intrusive) ───────────────────────────────────
    db_status = data.get("db_save_status", "")
    if db_status == "not_saved" or db_status == "unavailable":
        st.caption("ℹ️ Report could not be saved to the database (MongoDB unavailable). Your results are shown above.")
