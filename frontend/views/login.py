import base64
from pathlib import Path
import streamlit as st
from config import APP_NAME, APP_TAGLINE, SECONDARY_TAGLINE
from utils.session import login_user

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.jpg"

def _logo_b64() -> str:
    if _LOGO_PATH.exists():
        return base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    return ""

_LOGIN_CSS = """
<style>
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 22px rgba(6,182,212,0.45), 0 8px 24px rgba(0,0,0,0.55); }
    50%       { box-shadow: 0 0 48px rgba(6,182,212,0.85), 0 8px 24px rgba(0,0,0,0.55); }
}


/* ── CENTERED LOGO ────────────────────────────────────────── */
/* Force the Streamlit column block itself to center its children */
[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
}
.cricfit-logo-wrap {
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 4px 0 6px 0;
}
.cricfit-logo-card {
    width: 76px;
    height: 76px;
    border-radius: 18px;
    border: 2px solid rgba(6,182,212,0.65);
    background: #040e26;
    animation: pulse-glow 3s ease-in-out infinite;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    padding: 0;
    margin: 0 auto;
    box-sizing: border-box;
}
.cricfit-logo-card img,
.cricfit-logo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
    border-radius: 16px;
    display: block;
    margin: 0;
    padding: 0;
}

/* ── HERO TEXT ───────────────────────────────── */
.cricfit-hero {
    text-align: center;
    padding: 0;
    width: 100%;
}

/* ── FEATURE PILLS ───────────────────────────── */
.feature-pill {
    display: inline-block;
    background: rgba(6,182,212,0.1);
    border: 1px solid rgba(6,182,212,0.25);
    color: #06B6D4;
    padding: 3px 10px;
    border-radius: 16px;
    font-size: 0.72rem;
    font-weight: 700;
    margin: 2px;
}



/* ── TABS: NO underline / NO bottom border anywhere ─ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    background: transparent !important;
    border: none !important;
    border-bottom: none !important;
    padding: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: none !important;
    border-radius: 0 !important;
    padding: 6px 18px !important;
    margin-bottom: 0 !important;
    transition: color 0.2s ease !important;
    position: relative !important;
    cursor: pointer !important;
    box-shadow: none !important;
    outline: none !important;
}
/* Inactive tab text — bold, clearly readable */
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] * {
    color: #CBD5E1 !important;
    font-weight: bold !important;
    font-size: 0.85rem !important;
    background: none !important;
    -webkit-text-fill-color: #CBD5E1 !important;
    text-shadow: none !important;
    border: none !important;
}
/* Hover state — no underline, just brighter text */
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(6,182,212,0.05) !important;
    border: none !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"]:hover p,
.stTabs [data-baseweb="tab"]:hover span,
.stTabs [data-baseweb="tab"]:hover * {
    color: #F1F5F9 !important;
    -webkit-text-fill-color: #F1F5F9 !important;
    text-shadow: none !important;
}
/* Active tab: bold white text ONLY — absolutely no underline or border */
.stTabs [aria-selected="true"] {
    background: transparent !important;
    border: none !important;
    border-bottom: none !important;
    box-shadow: none !important;
    outline: none !important;
}
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] * {
    color: #FFFFFF !important;
    font-weight: bold !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-shadow: none !important;
    border: none !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 10px !important;
}
/* Nuke ALL Streamlit tab indicator elements */
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"],
div[data-baseweb="tab-highlight"],
div[data-testid="stTabIndicator"] {
    display: none !important;
    height: 0 !important;
    border: none !important;
    background: none !important;
    background-color: transparent !important;
}
.stTabs button[data-baseweb="tab"]::after,
.stTabs button[data-baseweb="tab"]::before,
.stTabs div[data-baseweb="tab-list"]::after,
.stTabs div[data-baseweb="tab-list"]::before {
    display: none !important;
}

/* ── HIDE HEADING ANCHOR ICON ────────────────── */
[data-testid="StyledLinkIconContainer"] {
    display: none !important;
}

</style>
"""

def render_login_page():
    """Render Login & Register authentication interface."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # ── Centered 3-column layout with compact width ──────────────────────────
    c1, c_mid, c2 = st.columns([1.2, 2.0, 1.2])
    with c_mid:
        # ── Hero: logo + title + badges in ONE block for guaranteed centering ──
        b64 = _logo_b64()
        logo_img = (
            f'<div class="cricfit-logo-card">'
            f'<img src="data:image/jpeg;base64,{b64}" class="cricfit-logo-img" '
            f'alt="CricFit AI Logo" />'
            f'</div>'
        ) if b64 else '<div style="font-size:2.8rem;">🏏</div>'

        st.markdown(
            f"""
            <div style="width:100%;text-align:center;padding:4px 0 10px 0;">
                <div class="cricfit-logo-wrap">
                    {logo_img}
                </div>
                <h1 style="font-size:2.1rem;font-weight:900;margin:0 0 2px 0;letter-spacing:-0.5px;
                           background:linear-gradient(100deg,#FFFFFF 30%,#06B6D4 100%);
                           -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    {APP_NAME}
                </h1>
                <p style="font-size:0.8rem;color:#06B6D4;font-weight:700;margin:3px 0 2px 0;
                          text-transform:uppercase;letter-spacing:1.5px;-webkit-text-fill-color:#06B6D4;">
                    {APP_TAGLINE}
                </p>
                <p style="font-size:0.78rem;color:#94A3B8;font-weight:500;margin:0 0 8px 0;
                          -webkit-text-fill-color:#94A3B8;">
                    {SECONDARY_TAGLINE}
                </p>
                <div style="margin-bottom:2px;">
                    <span class="feature-pill">🧠 AI Pose Estimation</span>
                    <span class="feature-pill">📊 Biomechanical Metrics</span>
                    <span class="feature-pill">💪 Real-time Analysis</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ── Auth Tabs ────────────────────────────────────────────────────────
        tab1, tab2 = st.tabs(["🔑  LOGIN", "✨  REGISTER"])

        with tab1:
            st.markdown(
                """
                <p style="color:#94A3B8; font-size:0.82rem; font-weight:500; margin-bottom:8px; text-align:center;">
                    Sign in to your CricFit AI athlete account.
                </p>
                """,
                unsafe_allow_html=True
            )
            with st.form("login_form"):
                email = st.text_input(
                    "Email Address",
                    value="",
                    placeholder="name@domain.com"
                )
                password = st.text_input(
                    "Password",
                    value="",
                    type="password"
                )
                submit_login = st.form_submit_button(
                    "🚀  LOGIN TO CRICFIT AI",
                    use_container_width=True,
                    type="primary"
                )
                if submit_login:
                    if not email or not email.strip():
                        st.error("Please enter your email address.")
                    elif not password:
                        st.error("Please enter your password.")
                    else:
                        login_user(email)

        with tab2:
            st.markdown(
                """
                <p style="color:#94A3B8; font-size:0.82rem; font-weight:500; margin-bottom:8px; text-align:center;">
                    Create your athlete account and start analyzing.
                </p>
                """,
                unsafe_allow_html=True
            )
            with st.form("register_form"):
                full_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
                reg_email = st.text_input("Email Address", placeholder="athlete@domain.com")
                reg_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submit_reg = st.form_submit_button(
                    "🏏  CREATE ATHLETE ACCOUNT",
                    use_container_width=True,
                    type="primary"
                )
                if submit_reg:
                    if not reg_email or not full_name:
                        st.error("Please fill in all required fields.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif reg_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        login_user(reg_email, name=full_name)

        st.markdown(
            """
            <div style="text-align:center; margin-top:10px; font-size:0.72rem; color:#64748B; line-height:1.4;">
                <span style="color:#475569;">CricFit AI · AI-Powered Cricket Fitness Analysis</span>
            </div>
            """,
            unsafe_allow_html=True
        )


