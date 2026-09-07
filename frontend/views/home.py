import streamlit as st
from config import PAGES
from utils.session import navigate_to

# Card hover animation CSS (injected once at top of home page)
_HOME_CSS = """


<style>
.activity-card {
    background: linear-gradient(145deg, rgba(15,23,42,0.92), rgba(30,41,59,0.85));
    border-radius: 22px;
    padding: 32px 28px;
    height: 100%;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s ease;
    position: relative;
    overflow: hidden;
}
.activity-card::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 60% 40%, rgba(6,182,212,0.06) 0%, transparent 60%);
    pointer-events: none;
}
.activity-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 30px rgba(6,182,212,0.12);
}
.card-batting { border: 1px solid rgba(6,182,212,0.25); }
.card-bowling { border: 1px solid rgba(59,130,246,0.25); }
.card-yoyo { border: 1px solid rgba(245,158,11,0.25); }
.card-injury { border: 1px solid rgba(239,68,68,0.25); }
.card-batting:hover { border-color: rgba(6,182,212,0.55); }
.card-bowling:hover { border-color: rgba(59,130,246,0.55); }
.card-yoyo:hover { border-color: rgba(245,158,11,0.55); }
.card-injury:hover { border-color: rgba(239,68,68,0.55); }
.how-step {
    background: rgba(30,41,59,0.55);
    padding: 20px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.05);
    transition: background 0.25s ease, border-color 0.25s ease;
}
.how-step:hover {
    background: rgba(30,41,59,0.85);
    border-color: rgba(6,182,212,0.2);
}
</style>
"""

def render_home_page():
    """Render Home selection screen with Batting and Bowling activity cards."""
    user = st.session_state.get("user", {})
    user_name = user.get("name", "Athlete")

    # Inject page CSS
    st.markdown(_HOME_CSS, unsafe_allow_html=True)
    
    st.markdown(
        f"""
        <div style="margin-bottom: 28px;">
            <h1 style="font-size: 2.2rem; font-weight: 900; margin: 0; color: #FFFFFF; line-height: 1.2;">
                Welcome back, {user_name} 👋
            </h1>
            <p style="font-size: 1.05rem; color: #94A3B8; margin-top: 8px;">
                Choose your cricket activity to begin your AI movement &amp; fitness analysis.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2, gap="large")
    
    # BATTING CARD
    with col1:

        st.markdown(
            """
            <div class="activity-card card-batting">
                <span style="position: absolute; top: 24px; right: 24px; background: rgba(6,182,212,0.15); color: #06B6D4; border: 1px solid rgba(6,182,212,0.5); padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px;">
                    ACTIVITY #1
                </span>
                <div style="font-size: 2.8rem; background: rgba(6,182,212,0.12); display: inline-flex; padding: 14px; border-radius: 18px; margin-bottom: 20px; border: 1px solid rgba(6,182,212,0.2);">
                    🏏
                </div>
                <h3 style="color: #FFFFFF; font-size: 1.7rem; font-weight: 800; margin: 0 0 10px 0; letter-spacing: -0.5px;">BATTING</h3>
                <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px; min-height: 54px;">
                    Analyze your batting movement, balance, hip mobility, core stability, and body control during stroke play.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🏏 START BATTING ANALYSIS", key="btn_home_batting", type="primary"):
            navigate_to(PAGES["BATTING"], activity="batting")

    # BOWLING CARD
    with col2:
        st.markdown(
            """
            <div class="activity-card card-bowling">
                <span style="position: absolute; top: 24px; right: 24px; background: rgba(59,130,246,0.15); color: #3B82F6; border: 1px solid rgba(59,130,246,0.5); padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px;">
                    ACTIVITY #2
                </span>
                <div style="font-size: 2.8rem; background: rgba(59,130,246,0.12); display: inline-flex; padding: 14px; border-radius: 18px; margin-bottom: 20px; border: 1px solid rgba(59,130,246,0.2);">
                    🏃
                </div>
                <h3 style="color: #FFFFFF; font-size: 1.7rem; font-weight: 800; margin: 0 0 10px 0; letter-spacing: -0.5px;">BOWLING</h3>
                <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px; min-height: 54px;">
                    Analyze your bowling run-up, delivery stride stability, trunk coordination, lower-body plant, and physical control.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🏃 START BOWLING ANALYSIS", key="btn_home_bowling", type="primary"):
            navigate_to(PAGES["BOWLING"], activity="bowling")

    st.markdown("<br>", unsafe_allow_html=True)
    
    col3, col4 = st.columns(2, gap="large")
    
    # YOYO TEST CARD
    with col3:
        st.markdown(
            """
            <div class="activity-card card-yoyo">
                <span style="position: absolute; top: 24px; right: 24px; background: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.5); padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px;">
                    ACTIVITY #3
                </span>
                <div style="font-size: 2.8rem; background: rgba(245,158,11,0.12); display: inline-flex; padding: 14px; border-radius: 18px; margin-bottom: 20px; border: 1px solid rgba(245,158,11,0.2);">
                    ⏱️
                </div>
                <h3 style="color: #FFFFFF; font-size: 1.7rem; font-weight: 800; margin: 0 0 10px 0; letter-spacing: -0.5px;">YOYO TEST</h3>
                <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px; min-height: 54px;">
                    Assess your endurance and cardiovascular fitness with the Yo-Yo Intermittent Recovery Test.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("⏱️ START YOYO TEST", key="btn_home_yoyo", type="primary"):
            navigate_to(PAGES["YOYO"], activity="yoyo")
            
    # INJURY DETECTION CARD
    with col4:
        st.markdown(
            """
            <div class="activity-card card-injury">
                <span style="position: absolute; top: 24px; right: 24px; background: rgba(239,68,68,0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.5); padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px;">
                    SCREENING
                </span>
                <div style="font-size: 2.8rem; background: rgba(239,68,68,0.12); display: inline-flex; padding: 14px; border-radius: 18px; margin-bottom: 20px; border: 1px solid rgba(239,68,68,0.2);">
                    🩺
                </div>
                <h3 style="color: #FFFFFF; font-size: 1.7rem; font-weight: 800; margin: 0 0 10px 0; letter-spacing: -0.5px;">INJURY DETECTION</h3>
                <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px; min-height: 54px;">
                    Identify possible injury concerns based on symptoms and receive appropriate next-step guidance.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🩺 CHECK FOR INJURY", key="btn_home_injury", type="primary"):
            navigate_to(PAGES["INJURY_DETECTION"])

    st.markdown("<br>", unsafe_allow_html=True)



    # HOW IT WORKS — use st.columns so grid is guaranteed to render
    st.markdown(

        """
        <div style="background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.07);
                    border-radius: 20px; padding: 24px 28px 8px 28px; margin-top: 8px;">
            <h4 style="color:#F8FAFC; margin:0 0 20px 0; font-size:1.15rem; font-weight:800; letter-spacing:-0.3px;">
                ⚡ HOW CRICFIT AI WORKS
            </h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Steps rendered inside the same visual container via columns
    with st.container():
        st.markdown(
            """<div style="background:rgba(15,23,42,0.6); border:1px solid rgba(255,255,255,0.07);
                           border-top:0; border-radius:0 0 20px 20px; padding:0 20px 24px 20px;">""",
            unsafe_allow_html=True
        )
        sc1, sc2, sc3, sc4 = st.columns(4)
        steps = [
            (sc1, "#06B6D4", "01", "📹 Upload Video",
             "Upload your batting or bowling action video clip."),
            (sc2, "#10B981", "02", "🧠 Pose Detection",
             "AI extracts frame-by-frame joint & movement biomechanics."),
            (sc3, "#8B5CF6", "03", "📊 Fitness Report",
             "Get 7 core movement metrics with an overall fitness score."),
            (sc4, "#F59E0B", "04", "💪 Personal Plan",
             "Follow AI-designed drills to improve & prevent injury."),
        ]
        for col, color, num, title, desc in steps:
            with col:
                st.markdown(
                    f"""
                    <div class="how-step" style="text-align:center; margin-bottom:8px;">
                        <div style="width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,0.04);
                                    border:1px solid {color}; color:{color}; font-size:0.8rem; font-weight:800;
                                    display:flex;align-items:center;justify-content:center;margin:0 auto 10px auto;">
                            {num}
                        </div>
                        <div style="font-size:0.9rem;font-weight:800;color:{color};margin-bottom:6px;">{title}</div>
                        <div style="font-size:0.8rem;color:#94A3B8;line-height:1.4;">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)

