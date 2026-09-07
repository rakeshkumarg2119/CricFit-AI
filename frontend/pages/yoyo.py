import time
import datetime
import streamlit as st
from config import PAGES, ALLOWED_VIDEO_TYPES
from utils.session import navigate_to, save_current_report
from utils.helpers import format_file_size

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
    """Render Yo-Yo Test page with Back to Home navigation and score estimator."""
    
    # ── Back to Home ──────────────────────────────────────────────────────────
    if st.button("← Back to Home", key="btn_yoyo_back_home", type="secondary"):
        navigate_to(PAGES["HOME"])

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                ⏱️ Yo-Yo Intermittent Recovery Test
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
                Assess your aerobic capacity, cardiovascular endurance, and cricket match-readiness fitness level.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── Preview Banner ────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 16px; padding: 24px; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
                <span style="background: rgba(245,158,11,0.2); color: #F59E0B; border: 1px solid rgba(245,158,11,0.5); padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.5px;">
                    MODULE IN PREVIEW
                </span>
                <span style="color: #94A3B8; font-size: 0.85rem; font-weight: 600;">Upcoming Feature</span>
            </div>
            <h3 style="color: #FFFFFF; margin: 6px 0 10px 0; font-size: 1.35rem; font-weight: 800;">
                AI-Driven Yo-Yo Endurance Assessment
            </h3>
            <p style="color: #CBD5E1; font-size: 0.95rem; line-height: 1.6; margin: 0;">
                The Yo-Yo Intermittent Recovery Test (Level 1) is the international gold standard used by national cricket boards worldwide. 
                CricFit AI is integrating computer vision pose tracking and automated audio pacing to track your speed, turning deceleration, and cardiovascular recovery.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 3 Benchmark Stat Cards ────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 22px; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 8px;">📏</div>
                <h4 style="color: #F8FAFC; margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 700;">TEST FORMAT</h4>
                <p style="color: #06B6D4; font-size: 1.4rem; font-weight: 800; margin: 0 0 6px 0;">2 × 20 Meters</p>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.5; margin: 0;">
                    Consecutive out-and-back shuttle runs with a strict 10-second active recovery walk interval.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 22px; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 8px;">🎯</div>
                <h4 style="color: #F8FAFC; margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 700;">PRO BENCHMARK</h4>
                <p style="color: #10B981; font-size: 1.4rem; font-weight: 800; margin: 0 0 6px 0;">16.5 – 17.2</p>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.5; margin: 0;">
                    Standard qualification score for senior professional and international cricket athletes.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 22px; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 8px;">🫀</div>
                <h4 style="color: #F8FAFC; margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 700;">FITNESS OUTPUT</h4>
                <p style="color: #F59E0B; font-size: 1.4rem; font-weight: 800; margin: 0 0 6px 0;">Endurance &amp; Fitness</p>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.5; margin: 0;">
                    Measures aerobic endurance, Yo-Yo performance level, and overall fitness based on the analyzed test.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Interactive Quick Estimator Card ──────────────────────────────────────
    with st.container(border=True):
        st.subheader("⚡ Quick Yo-Yo Score Checker")
        st.caption("Select a completed Yo-Yo test level to preview fitness category, estimated distance, shuttles, and fitness score:")

        col_input, col_result = st.columns([1, 1.2], gap="large")

        with col_input:
            level = st.selectbox(
                "Select Yo-Yo Test Level",
                options=list(YOYO_BENCHMARKS.keys()),
                index=3,
                key="yoyo_level_select"
            )
            data = YOYO_BENCHMARKS.get(level, YOYO_BENCHMARKS["16.5 (National Squad Cutoff)"])

            uploaded_file = st.file_uploader(
                "UPLOAD YO-YO TEST VIDEO",
                type=ALLOWED_VIDEO_TYPES,
                key="yoyo_uploader",
                help="Upload a video of your completed Yo-Yo test for analysis."
            )
            
            if uploaded_file is not None:
                st.markdown(
                    f"""
                    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 16px; padding: 20px; margin: 20px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div>
                                <span style="font-size: 0.75rem; color: #10B981; font-weight: 700;">✓ VIDEO READY</span>
                                <h4 style="margin: 4px 0 0 0; color: #FFFFFF; font-size: 1.1rem;">{uploaded_file.name}</h4>
                            </div>
                            <span style="background: #1E293B; color: #94A3B8; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem;">
                                Size: {format_file_size(uploaded_file.size)}
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.video(uploaded_file)
                st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.markdown(
                    """
                    <div style="border: 2px dashed rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 30px; text-align: center; background: rgba(15, 23, 42, 0.4); margin-top: 10px; margin-bottom: 20px;">
                        <div style="font-size: 2.5rem; margin-bottom: 10px;">📹</div>
                        <h4 style="color: #F8FAFC; margin: 0 0 8px 0; font-size: 1.1rem;">Upload Yo-Yo Test Video</h4>
                        <p style="color: #94A3B8; font-size: 0.85rem; margin: 0;">
                            Upload a video of your completed Yo-Yo test for analysis.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            if st.button("ANALYZE YO-YO TEST", key="btn_analyze_yoyo", type="primary", use_container_width=True):
                pass

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
            m3.metric("Fitness Score", str(data["vo2_max"]))

            st.caption("Standard Yo-Yo IR1 Cricket Benchmark (Level 16.5 = National Baseline)")
