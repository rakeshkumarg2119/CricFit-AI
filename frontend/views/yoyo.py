"""
CRICFIT AI — Yo-Yo Intermittent Recovery Test Page
==================================================
Features:
1. AI Video Shuttle Tracker: Upload test footage to track step cadence,
   detect 180° turns, monitor 10s rest compliance, and query Groq for aerobic conditioning.
2. Quick Benchmark Score Checker: Interactive tool to check standard national squad baselines.
"""

import time
import datetime
import streamlit as st
from config import PAGES, ALLOWED_VIDEO_TYPES
from utils.session import navigate_to, save_current_report
from utils.helpers import validate_video_file, format_file_size
from services.api import analyze_video
from components.report_view import render_full_report_view

# ── Structured Yo-Yo IR1 Cricket Benchmarks ──────────────────────────────────
YOYO_BENCHMARKS = {
    "14.1 (Club Level)": {
        "status": "BELOW CRICKET COMPETITIVE STANDARD",
        "category": "error",
        "distance_m": 680,
        "shuttles": 17,
        "vo2_max": 42.1,
        "score_100": 45,
        "detail": "Foundational aerobic base. Requires structured cardiovascular conditioning to reach competitive standard."
    },
    "15.3 (Intermediate)": {
        "status": "DEVELOPMENT TIER (NEEDS CONDITIONING)",
        "category": "warning",
        "distance_m": 1000,
        "shuttles": 25,
        "vo2_max": 44.8,
        "score_100": 60,
        "detail": "Approaching domestic league pace. Increased shuttle intervals recommended for match-long stamina."
    },
    "16.1 (Domestic Standard)": {
        "status": "ACCEPTABLE (DOMESTIC STANDARD)",
        "category": "warning",
        "distance_m": 1240,
        "shuttles": 31,
        "vo2_max": 46.8,
        "score_100": 72,
        "detail": "Meets basic domestic cricket benchmark; requires extra stamina for multi-day matches and fast-bowling workloads."
    },
    "16.5 (National Squad Cutoff)": {
        "status": "MATCH READY (QUALIFIED CUTOFF)",
        "category": "success",
        "distance_m": 1400,
        "shuttles": 35,
        "vo2_max": 48.2,
        "score_100": 85,
        "detail": "Meets BCCI / international squad baseline standard. Fully qualified for senior competitive selection."
    },
    "17.1 (Elite Cricket Standard)": {
        "status": "ELITE STANDARD (HIGH PERFORMANCE)",
        "category": "info",
        "distance_m": 1600,
        "shuttles": 40,
        "vo2_max": 49.8,
        "score_100": 92,
        "detail": "Top-tier aerobic capacity. Outstanding high-intensity recovery between bowling spells and long innings."
    },
    "18.2+ (Peak International)": {
        "status": "PEAK INTERNATIONAL ATHLETE",
        "category": "info",
        "distance_m": 1960,
        "shuttles": 49,
        "vo2_max": 52.9,
        "score_100": 98,
        "detail": "World-class endurance level. Matches the highest tier of international cricket athletes."
    },
}


def render_yoyo_page():
    """Render Yo-Yo Test page with Video Analysis and Quick Estimator."""

    if st.button("← Back to Home", key="btn_yoyo_back_home", type="secondary"):
        navigate_to(PAGES["HOME"])

    # Show report if already analyzed for yoyo
    rep = st.session_state.get("analysis_result")
    if rep and str(rep.get("activity", "")).lower() in ("yoyo", "yoyo_test"):
        def reset_analysis():
            st.session_state.analysis_result = None
            st.session_state.uploaded_video = None
            st.rerun()

        try:
            render_full_report_view(rep, on_reset_callback=reset_analysis)
        except Exception as e:
            st.error(f"⚠️ Error displaying analysis report: {e}")
            if st.button("🔄 Try Uploading Again", key="btn_err_reset_yoyo"):
                reset_analysis()
        return

    st.html("""
    <div style="margin-bottom:24px;">
        <h1 style="font-size:2.2rem;font-weight:900;margin:0;color:#FFFFFF;">
            &#x23F1;&#xFE0F; Yo-Yo Intermittent Recovery Test
        </h1>
        <p style="font-size:1.05rem;color:#94A3B8;margin-top:6px;">
            Assess your aerobic capacity, shuttle cadence consistency, and match-readiness fitness
            level using computer vision tracking.
        </p>
    </div>
    """)

    tab_video, tab_checker = st.tabs(["📹 AI Video Shuttle Tracker", "⚡ Quick Score Benchmark"])

    # ── TAB 1: AI Video Shuttle Tracker ───────────────────────────────────────
    with tab_video:
        st.html("""
        <p style="color:#94A3B8;font-size:0.95rem;margin-bottom:16px;">
            Upload a video of your 20m Yo-Yo shuttle runs. CricFit AI will track your step frequency,
            monitor mandatory 10-second rest intervals, and generate custom conditioning plans.
        </p>
        """)

        col_up, col_lvl = st.columns([2, 1])
        with col_lvl:
            target_level = st.selectbox(
                "Target / Reported Yo-Yo Level",
                options=["14.1", "15.3", "16.1", "16.5", "17.1", "18.2"],
                index=3,
                key="yoyo_video_level_select",
                help="The level you are aiming for or completed during this recorded session."
            )

        with col_up:
            uploaded_file = st.file_uploader(
                "Upload Yo-Yo Test Footage",
                type=ALLOWED_VIDEO_TYPES,
                key="yoyo_uploader",
                help="Upload MP4, MOV, or AVI 20m shuttle clip (Max 100MB)"
            )

        if uploaded_file is not None:
            is_valid, msg = validate_video_file(uploaded_file)
            if not is_valid:
                st.error(msg)
            else:
                col_v1, col_v2, col_v3 = st.columns([1, 2.2, 1])
                with col_v2:
                    st.video(uploaded_file)

                if st.button("🚀 TRACK YO-YO CADENCE & RECOVERY", key="btn_run_yoyo_analysis",
                             type="primary"):

                    with st.status("🤖 Tracking Step Cadence, Turn Dynamics & Rest Compliance with Groq AI...", expanded=True) as status:
                        st.write("Step 1/3: Analyzing MediaPipe ankle bob & 20m sprint intervals...")
                        success, report_data, err_msg = analyze_video(
                            uploaded_file,
                            activity_type="yoyo",
                            yoyo_level=target_level
                        )

                        if success and report_data:
                            status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                            st.session_state.analysis_result = report_data
                            st.session_state.selected_activity = "yoyo"
                            st.rerun()
                        else:
                            status.update(label="❌ Analysis Failed", state="error", expanded=True)
                            st.error(f"❌ {err_msg}")

    # ── TAB 2: Quick Benchmark Estimator ──────────────────────────────────────
    with tab_checker:
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            st.html("""
            <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
                        border-radius:16px;padding:20px;">
                <div style="font-size:1.5rem;margin-bottom:4px;">&#x1F4CF;</div>
                <h5 style="color:#94A3B8;margin:0 0 4px 0;font-size:0.8rem;font-weight:700;">TEST FORMAT</h5>
                <p style="color:#06B6D4;font-size:1.2rem;font-weight:800;margin:0;">2 &times; 20 Meters</p>
            </div>
            """)
        with c2:
            st.html("""
            <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
                        border-radius:16px;padding:20px;">
                <div style="font-size:1.5rem;margin-bottom:4px;">&#x1F3AF;</div>
                <h5 style="color:#94A3B8;margin:0 0 4px 0;font-size:0.8rem;font-weight:700;">PRO BENCHMARK</h5>
                <p style="color:#10B981;font-size:1.2rem;font-weight:800;margin:0;">16.5 &ndash; 17.2</p>
            </div>
            """)
        with c3:
            st.html("""
            <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(255,255,255,0.08);
                        border-radius:16px;padding:20px;">
                <div style="font-size:1.5rem;margin-bottom:4px;">&#x1FAC0;</div>
                <h5 style="color:#94A3B8;margin:0 0 4px 0;font-size:0.8rem;font-weight:700;">FITNESS OUTPUT</h5>
                <p style="color:#F59E0B;font-size:1.2rem;font-weight:800;margin:0;">VO&#x2082; Max &amp; Speed</p>
            </div>
            """)

        with st.container(border=True):
            st.subheader("⚡ Quick Yo-Yo Score Checker")
            col_input, col_result = st.columns([1, 1.2], gap="large")

            with col_input:
                level = st.selectbox(
                    "Select Completed Yo-Yo Level",
                    options=list(YOYO_BENCHMARKS.keys()),
                    index=3,
                    key="yoyo_level_select"
                )
                data = YOYO_BENCHMARKS.get(level, YOYO_BENCHMARKS["16.5 (National Squad Cutoff)"])
                st.info(f"**Target Overview**\n\n{data['detail']}")

                if st.button("💾 Log Score to History", key="btn_save_yoyo_report",
                             use_container_width=True, type="primary"):
                    report_id = f"YY-{int(time.time()) % 100000:05d}"
                    report_entry = {
                        "id": report_id,
                        "activity": "Yo-Yo Test",
                        "date_str": datetime.date.today().strftime("%d %b %Y"),
                        "overall_score": data["score_100"],
                        "movement_quality": data["score_100"],
                        "risk_level": "Low" if data["score_100"] >= 75 else "Moderate",
                        "metrics": {
                            "balance": min(95, data["score_100"] + 2),
                            "lower_body_stability": data["score_100"],
                            "hip_mobility": min(90, data["score_100"] - 4),
                            "core_stability": data["score_100"],
                            "coordination": min(95, data["score_100"] + 5),
                            "body_symmetry": 85,
                            "movement_quality": data["score_100"],
                        },
                        "strengths": [
                            f"Recorded level {level} with estimated VO\u2082 max of {data['vo2_max']} mL/kg/min.",
                            f"Completed {data['shuttles']} shuttles ({data['distance_m']} meters) under standard pacing."
                        ],
                        "areas_to_improve": [
                            {
                                "area": "Deceleration Recovery",
                                "score": data["score_100"],
                                "priority": "High" if data["score_100"] < 80 else "Medium",
                                "explanation": "Focus on 180\u00b0 turning mechanics to minimize braking fatigue on knees."
                            }
                        ],
                        "ai_summary": f"Yo-Yo IR1 test performance evaluated at {level} ({data['distance_m']}m). Status: {data['status']}.",
                        "exercises": [
                            {
                                "exercise_name": "High-Intensity Interval Sprints",
                                "target_area": "VO\u2082 Max & Lactate Recovery",
                                "sets_and_reps": "4 sets \u00d7 6 reps (30s sprint / 30s walk)",
                                "difficulty": "Intermediate",
                                "how_it_improves": "Elevates aerobic ceiling and rapid cardiovascular recovery."
                            }
                        ],
                        "nutrition_plan": {
                            "pre_workout": "Complex oats with banana 2 hours before running.",
                            "post_workout": "High protein recovery shake + electrolytes within 45m."
                        }
                    }
                    save_current_report(report_entry)
                    st.success(f"✅ Level {level} saved to your report history! (ID: {report_id})")

            with col_result:
                data = YOYO_BENCHMARKS.get(level, YOYO_BENCHMARKS["16.5 (National Squad Cutoff)"])
                cat = data.get("category", "info")
                status_text = data.get("status", "STANDARD")

                if cat == "success":
                    st.success(f"**{status_text}**", icon="✅")
                elif cat == "warning":
                    st.warning(f"**{status_text}**", icon="⚠️")
                elif cat == "error":
                    st.error(f"**{status_text}**", icon="❌")
                else:
                    st.info(f"**{status_text}**", icon="🌟")

                m1, m2, m3 = st.columns(3)
                m1.metric("Distance", f"{data['distance_m']:,} m")
                m2.metric("Shuttles", str(data["shuttles"]))
                m3.metric("Est. VO\u2082 Max", str(data["vo2_max"]))
