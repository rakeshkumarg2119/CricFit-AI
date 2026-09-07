import sys
from pathlib import Path

# Ensure frontend directory is at the head of sys.path
_FRONTEND_DIR = Path(__file__).resolve().parent
if str(_FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(_FRONTEND_DIR))

import streamlit as st
from config import APP_NAME, APP_TAGLINE, PAGES
from utils.session import init_session_state
from components.navbar import render_navbar
from components.sidebar import render_sidebar

# Import Page Views
from pages.login import render_login_page
from pages.home import render_home_page
from pages.batting import render_batting_page
from pages.bowling import render_bowling_page
from pages.yoyo import render_yoyo_page
from pages.injury_detection import render_injury_detection_page
from pages.reports import render_reports_page
from pages.progress import render_progress_page
from pages.profile import render_profile_page

# Page Configuration
st.set_page_config(
    page_title=f"{APP_NAME} - {APP_TAGLINE}",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Sports-Tech Design System Injection
st.markdown(
    """
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ===== MAIN BACKGROUND ===== */
    .stApp {
        background: #0B0F19;
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -10%, rgba(6,182,212,0.12) 0%, transparent 70%),
            radial-gradient(ellipse 60% 40% at 90% 80%, rgba(59,130,246,0.08) 0%, transparent 60%);
        color: #F8FAFC;
    }

    /* ===== TYPOGRAPHY ===== */
    h1, h2, h3, h4, h5, h6, p, div:not([data-testid="stInputIcon"]):not([class*="Material"]) {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #070C17 0%, #0B0F1E 100%) !important;
        border-right: 1px solid rgba(6,182,212,0.15) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }
    /* Sidebar button — default (not active) */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        text-align: left !important;
        margin-bottom: 4px;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(6,182,212,0.12) !important;
        border-color: rgba(6,182,212,0.4) !important;
        color: #06B6D4 !important;
        transform: translateX(4px) !important;
    }
    /* Active nav button (primary type in sidebar) */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, rgba(6,182,212,0.25), rgba(59,130,246,0.15)) !important;
        border: 1px solid rgba(6,182,212,0.5) !important;
        color: #06B6D4 !important;
        box-shadow: 0 0 12px rgba(6,182,212,0.15) !important;
    }

    /* ===== MAIN BUTTONS ===== */
    .stButton > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        padding: 0.65rem 1.4rem !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        letter-spacing: 0.3px !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #06B6D4 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(6,182,212,0.35), inset 0 1px 0 rgba(255,255,255,0.15) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 8px 28px rgba(6,182,212,0.5) !important;
    }
    .stButton > button[kind="primary"]:active {
        transform: translateY(0) scale(0.99) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(30,41,59,0.7) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(51,65,85,0.85) !important;
        border-color: #06B6D4 !important;
        color: #06B6D4 !important;
        transform: translateY(-1px) !important;
    }

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        background: rgba(15,23,42,0.6) !important;
        border: 2px dashed rgba(6,182,212,0.35) !important;
        border-radius: 18px !important;
        padding: 20px !important;
        transition: border-color 0.3s ease !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(6,182,212,0.7) !important;
    }

    /* ===== FORM LABELS & INPUTS ===== */
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] label p,
    .stTextInput label,
    .stTextInput label p {
        color: #E2E8F0 !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px !important;
        margin-bottom: 4px !important;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea textarea {
        background: rgba(15,23,42,0.85) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #64748B !important;
        opacity: 1 !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #06B6D4 !important;
        box-shadow: 0 0 0 3px rgba(6,182,212,0.25) !important;
    }

    /* ===== PASSWORD VISIBILITY BUTTON & ICON ===== */
    [data-testid="stTextInput"] button {
        background: transparent !important;
        border: none !important;
        color: #94A3B8 !important;
        outline: none !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 8px !important;
        cursor: pointer !important;
        transition: color 0.2s ease !important;
    }
    [data-testid="stTextInput"] button:hover {
        color: #06B6D4 !important;
        background: transparent !important;
    }
    [data-testid="stTextInput"] button *,
    [data-testid="stTextInput"] button span,
    .material-symbols-rounded,
    [data-aria-hidden="true"] {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: 1.25rem !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-smoothing: antialiased !important;
    }

    /* ===== TABS (base — no underlines, bold text only) ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: transparent;
        border: none !important;
        border-bottom: none !important;
        padding: 0;
        border-radius: 0;
        box-shadow: none;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        border-bottom: none !important;
        border-radius: 0 !important;
        padding: 10px 24px !important;
        margin-bottom: 0 !important;
        transition: color 0.2s ease !important;
        box-shadow: none !important;
        outline: none !important;
    }
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] * {
        color: #CBD5E1 !important;
        font-weight: bold !important;
        font-size: 0.9rem !important;
        background: none !important;
        -webkit-text-fill-color: #CBD5E1 !important;
        text-shadow: none !important;
        border: none !important;
    }
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
    }
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
        padding-top: 20px;
    }
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
    /* Hide anchor link icon on headings */
    [data-testid="StyledLinkIconContainer"] {
        display: none !important;
    }

    /* ===== TOGGLE ===== */
    .stToggle > label {
        color: #94A3B8 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0B0F19; }
    ::-webkit-scrollbar-thumb { background: rgba(6,182,212,0.4); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #06B6D4; }

    /* ===== HIDE STREAMLIT CHROME ===== */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True
)

def main():
    """Main Application Entry Point."""
    init_session_state()
    
    # Check if user is logged in
    if not st.session_state.logged_in:
        render_login_page()
    else:
        render_sidebar()
        render_navbar()
        
        current_page = st.session_state.get("current_page", PAGES["HOME"])
        
        if current_page == PAGES["HOME"]:
            render_home_page()
        elif current_page == PAGES["BATTING"]:
            render_batting_page()
        elif current_page == PAGES["BOWLING"]:
            render_bowling_page()
        elif current_page == PAGES["YOYO"]:
            render_yoyo_page()
        elif current_page == PAGES["INJURY_DETECTION"]:
            render_injury_detection_page()
        elif current_page == PAGES["REPORTS"]:
            render_reports_page()
        elif current_page == PAGES["PROGRESS"]:
            render_progress_page()
        elif current_page == PAGES["PROFILE"]:
            render_profile_page()
        else:
            render_home_page()

if __name__ == "__main__":
    main()
