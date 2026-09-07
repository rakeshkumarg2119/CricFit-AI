import time
import streamlit as st
from config import ALLOWED_VIDEO_TYPES, PAGES
from utils.session import navigate_to
from utils.helpers import validate_video_file, format_file_size
from services.api import analyze_video
from components.report_view import render_full_report_view

def render_bowling_page():
    """Render Bowling Analysis video upload & processing page."""
    
    # ── Back to Home ──────────────────────────────────────────────────────────
    if st.button("← Back to Home", key="btn_bowling_back_home", type="secondary"):
        navigate_to(PAGES["HOME"])

    # Check if report already generated for active session
    if st.session_state.get("analysis_result") and st.session_state.get("selected_activity") == "bowling":
        def reset_analysis():
            st.session_state.analysis_result = None
            st.session_state.uploaded_video = None
            st.rerun()
            
        render_full_report_view(st.session_state.analysis_result, on_reset_callback=reset_analysis)
        return

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF;">
                🏃 Bowling Analysis
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 6px;">
                Upload your bowling video and let CricFit AI analyze your stride plant, trunk balance, stability, and delivery coordination.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    uploaded_file = st.file_uploader(
        "Upload Bowling Video",
        type=ALLOWED_VIDEO_TYPES,
        key="bowling_uploader",
        help="Upload MP4, MOV, or AVI bowling run-up and delivery clip (Max 100MB)"
    )
    
    st.button("ANALYZE BOWLING", key="btn_analyze_bowling_placeholder", type="primary", use_container_width=True)
    
    if uploaded_file is not None:
        is_valid, msg = validate_video_file(uploaded_file)
        if not is_valid:
            st.error(msg)
            return
            
        st.session_state.uploaded_video = uploaded_file
        
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 16px; padding: 20px; margin: 20px 0;">
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
        
        if st.button("ANALYZE BOWLING", key="btn_analyze_bowling", type="primary", use_container_width=True):
            pass
    else:
        st.markdown(
            """
            <div style="border: 2px dashed rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 40px; text-align: center; background: rgba(15, 23, 42, 0.4); margin-top: 20px;">
                <div style="font-size: 3rem; margin-bottom: 10px;">📹</div>
                <h4 style="color: #F8FAFC; margin: 0 0 8px 0;">Upload your Bowling Video</h4>
                <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
                    Select a high-quality video clip showing your run-up, delivery stride plant, and follow-through.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
