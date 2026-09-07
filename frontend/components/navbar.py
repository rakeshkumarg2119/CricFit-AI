import streamlit as st
from config import APP_NAME, APP_TAGLINE, PAGES
from utils.session import navigate_to, logout_user

def render_navbar():
    """Render top branding navbar header with athlete info, navigation bar, and sign out."""
    user = st.session_state.get("user") or {}
    user_name = user.get("name", "Athlete")
    current_page = st.session_state.get("current_page", PAGES["HOME"])

    # ── Top Row: Brand, Athlete Profile, Logout ──────────────────────────────
    col1, col2 = st.columns([2, 2])
    
    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
                <div style="background: linear-gradient(135deg, #06B6D4, #3B82F6); padding: 8px 14px; border-radius: 12px; font-weight: 900; font-size: 1.4rem; color: white; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);">
                    🏏 CF
                </div>
                <div>
                    <h2 style="margin: 0; padding: 0; font-weight: 800; font-size: 1.4rem; background: linear-gradient(90deg, #FFFFFF, #94A3B8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        {APP_NAME}
                    </h2>
                    <p style="margin: 0; font-size: 0.8rem; color: #94A3B8; font-weight: 500;">
                        {APP_TAGLINE}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        c_badge, c_logout = st.columns([2.8, 1.2])
        with c_badge:
            st.markdown(
                f"""
                <div style="text-align: right; padding-top: 6px;">
                    <span style="background: rgba(6,182,212,0.12); color: #06B6D4; border: 1px solid rgba(6,182,212,0.3); padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; margin-right: 6px;">
                        👤 {user_name}
                    </span>
                    <span style="background: #064E3B; color: #10B981; border: 1px solid #10B981; padding: 4px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600;">
                        FASTAPI
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c_logout:
            if st.button("🚪 Logout", key="nav_btn_logout", help="Sign out of CricFit AI"):
                logout_user()

    # ── Bottom Row: Main App Navigation Tabs ─────────────────────────────────
    nav_items = [
        ("🏠 Home", PAGES["HOME"], None),
        ("🏏 Batting", PAGES["BATTING"], "batting"),
        ("🏃 Bowling", PAGES["BOWLING"], "bowling"),
        ("⏱️ Yo-Yo", PAGES["YOYO"], "yoyo"),
        ("🩺 Injury", PAGES["INJURY_DETECTION"], None),
        ("📜 History & Reports", PAGES["REPORTS"], None),
        ("📈 Progress", PAGES["PROGRESS"], None),
        ("👤 Profile", PAGES["PROFILE"], None),
    ]

    cols = st.columns(len(nav_items))
    for i, (label, page_key, activity) in enumerate(nav_items):
        is_active = (current_page == page_key)
        btn_type = "primary" if is_active else "secondary"
        with cols[i]:
            if st.button(label, key=f"topnav_{page_key}", type=btn_type):
                if not is_active:
                    navigate_to(page_key, activity=activity)

    st.markdown("<hr style='border: 0; height: 1px; background: rgba(255, 255, 255, 0.08); margin: 10px 0 22px 0;' />", unsafe_allow_html=True)

