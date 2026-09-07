"""
CRICFIT AI — Batting Analysis Page
==================================
Allows cricketers to upload batting stroke videos, run them through the
Keras GRU Classifier + FastDTW Stage 2 reference matcher + Groq AI analysis,
and review the annotated skeleton video, tailored drills, diet plan, and PDF report.
"""

import time
import streamlit as st
from config import ALLOWED_VIDEO_TYPES, PAGES
from utils.session import navigate_to
from utils.helpers import validate_video_file, format_file_size
from services.api import analyze_video
from components.report_view import render_full_report_view


def render_batting_page():
    """Render Batting Analysis video upload & processing page."""

    if st.button("← Back to Home", key="btn_batting_back_home", type="secondary"):
        navigate_to(PAGES["HOME"])

    # Show report if already analyzed for batting
    rep = st.session_state.get("analysis_result")
    if rep and str(rep.get("activity", "")).lower() == "batting":
        def reset_analysis():
            st.session_state.analysis_result = None
            st.session_state.uploaded_video = None
            st.rerun()

        try:
            render_full_report_view(rep, on_reset_callback=reset_analysis)
        except Exception as e:
            st.error(f"⚠️ Error displaying analysis report: {e}")
            if st.button("🔄 Try Uploading Again", key="btn_err_reset_batting"):
                reset_analysis()
        return

    st.html("""
    <div style="margin-bottom:24px;">
        <h1 style="font-size:2.2rem;font-weight:900;margin:0;color:#FFFFFF;">
            &#x1F3CF; Batting Biomechanics Analysis
        </h1>
        <p style="font-size:1.05rem;color:#94A3B8;margin-top:6px;">
            Upload your batting stroke clip. CricFit AI will classify your shot, measure kinetic
            transfer and stability, and generate Groq AI coaching drills, diet plans, and
            annotated video feedback.
        </p>
    </div>
    """)

    uploaded_file = st.file_uploader(
        "Upload Batting Video",
        type=ALLOWED_VIDEO_TYPES,
        key="batting_uploader",
        help="Upload MP4, MOV, or AVI batting stroke clip (Max 100MB)"
    )

    if uploaded_file is not None:
        is_valid, msg = validate_video_file(uploaded_file)
        if not is_valid:
            st.error(msg)
            return

        st.session_state.uploaded_video = uploaded_file

        st.html(f"""
        <div style="background:rgba(15,23,42,0.8);border:1px solid rgba(6,182,212,0.3);
                    border-radius:16px;padding:20px;margin:20px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <div>
                    <span style="font-size:0.75rem;color:#10B981;font-weight:700;">
                        &#x2713; VIDEO READY FOR AI PIPELINE</span>
                    <h4 style="margin:4px 0 0 0;color:#FFFFFF;font-size:1.1rem;">{uploaded_file.name}</h4>
                </div>
                <span style="background:#1E293B;color:#94A3B8;padding:4px 10px;
                             border-radius:12px;font-size:0.8rem;">
                    Size: {format_file_size(uploaded_file.size)}
                </span>
            </div>
        </div>
        """)

        col_v1, col_v2, col_v3 = st.columns([1, 2.2, 1])
        with col_v2:
            st.video(uploaded_file)

        if st.button("🚀 ANALYZE BATTING STROKE", key="btn_run_batting_analysis",
                     type="primary"):

            with st.status("🤖 Running AI Vision Shot Classifier, FastDTW Biomechanics & Groq AI...", expanded=True) as status:
                st.write("Step 1/3: Extracting MediaPipe Pose Keypoints & Classifying Batting Stroke...")
                success, report_data, err_msg = analyze_video(uploaded_file, activity_type="batting")

                if success and report_data:
                    status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                    st.session_state.analysis_result = report_data
                    st.session_state.selected_activity = "batting"
                    st.session_state.uploaded_video = None
                    st.rerun()
                else:
                    status.update(label="❌ Analysis Failed", state="error", expanded=True)
                    st.error(f"❌ {err_msg}")
    else:
        st.html("""
        <div style="border:2px dashed rgba(255,255,255,0.15);border-radius:20px;padding:40px;
                    text-align:center;background:rgba(15,23,42,0.4);margin-top:20px;">
            <div style="font-size:3rem;margin-bottom:10px;">&#x1F4F9;</div>
            <h4 style="color:#F8FAFC;margin:0 0 8px 0;">Upload your Batting Video</h4>
            <p style="color:#94A3B8;font-size:0.9rem;margin:0;">
                Select a clear video clip showing your stance, downswing, impact point, and follow-through.
            </p>
        </div>
        """)
