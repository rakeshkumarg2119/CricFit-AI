import streamlit as st
from config import PAGES
from utils.session import navigate_to, logout_user

def render_sidebar():
    """Render custom Streamlit sidebar with navigation, athlete info, and quick stats."""
    with st.sidebar:

        # Brand Header
        st.markdown(
            """
            <div style="text-align:center; padding:8px 0 18px 0;">
                <div style="width:56px;height:56px;border-radius:16px;
                            background:linear-gradient(135deg,#06B6D4,#2563EB);
                            margin:0 auto 10px auto;display:flex;
                            align-items:center;justify-content:center;
                            font-size:1.8rem;
                            box-shadow:0 6px 20px rgba(6,182,212,0.4);">
                    🏏
                </div>
                <div style="font-size:1.2rem;font-weight:900;color:#FFFFFF;letter-spacing:-0.5px;">
                    CRICFIT AI
                </div>
                <div style="font-size:0.68rem;color:#06B6D4;font-weight:700;
                            text-transform:uppercase;letter-spacing:1.5px;margin-top:2px;">
                    AI Fitness Coach
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Athlete Card
        user = st.session_state.get("user") or {}
        user_name = user.get("name", "Athlete")
        user_email = user.get("email", "")
        report_count = len(st.session_state.get("report_history", []))

        st.markdown(
            f"""
            <div style="background:rgba(6,182,212,0.06);border:1px solid rgba(6,182,212,0.18);
                        border-radius:14px;padding:12px 14px;margin-bottom:18px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="width:36px;height:36px;border-radius:50%;
                                background:linear-gradient(135deg,#06B6D4,#2563EB);
                                display:flex;align-items:center;justify-content:center;
                                font-size:1rem;flex-shrink:0;">
                        🏏
                    </div>
                    <div style="overflow:hidden;">
                        <div style="font-weight:700;color:#F8FAFC;font-size:0.9rem;
                                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                            {user_name}
                        </div>
                        <div style="font-size:0.72rem;color:#06B6D4;
                                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                            {user_email}
                        </div>
                    </div>
                </div>
                <div style="margin-top:10px;padding-top:10px;
                            border-top:1px solid rgba(255,255,255,0.06);
                            display:flex;justify-content:space-around;">
                    <div style="text-align:center;">
                        <div style="font-size:1.1rem;font-weight:800;color:#06B6D4;">{report_count}</div>
                        <div style="font-size:0.65rem;color:#64748B;font-weight:600;">REPORTS</div>
                    </div>
                    <div style="width:1px;background:rgba(255,255,255,0.06);"></div>
                    <div style="text-align:center;">
                        <div style="font-size:1.1rem;font-weight:800;color:#10B981;">FASTAPI</div>
                        <div style="font-size:0.65rem;color:#64748B;font-weight:600;">BACKEND</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Navigation Label
        st.markdown(
            """<div style="font-size:0.7rem;color:#475569;font-weight:700;
                          text-transform:uppercase;letter-spacing:1.5px;
                          margin-bottom:8px;padding-left:4px;">
                NAVIGATION
            </div>""",
            unsafe_allow_html=True
        )

        current_page = st.session_state.get("current_page", PAGES["HOME"])

        nav_options = [
            ("🏠  Home", PAGES["HOME"]),
            ("🏏  Batting Analysis", PAGES["BATTING"]),
            ("🏃  Bowling Analysis", PAGES["BOWLING"]),
            ("⏱️  Yo-Yo Test", PAGES["YOYO"]),
            ("🩺  Injury Detection", PAGES["INJURY_DETECTION"]),
            ("📊  My Reports", PAGES["REPORTS"]),
            ("📈  Progress Tracking", PAGES["PROGRESS"]),
            ("👤  Profile", PAGES["PROFILE"]),
        ]

        for label, page_key in nav_options:
            is_active = current_page == page_key
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{page_key}",
                         use_container_width=True, type=btn_type):
                navigate_to(page_key)

        st.markdown(
            """<hr style="border:0;height:1px;
                          background:rgba(255,255,255,0.07);
                          margin:16px 0;">""",
            unsafe_allow_html=True
        )

        if st.button("🚪  Logout", key="btn_logout", use_container_width=True):
            logout_user()

        # Footer
        st.markdown(
            """
            <div style="margin-top:24px;text-align:center;
                        font-size:0.7rem;color:#334155;line-height:1.6;
                        padding:10px;border-top:1px solid rgba(255,255,255,0.04);">
                CricFit AI v1.0<br>
                <span style="color:#1E3A5F;">Keras · Pose Estimation · FastAPI</span>
            </div>
            """,
            unsafe_allow_html=True
        )
