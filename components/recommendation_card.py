import streamlit as st

def render_recommendation_card(exercise):
    """
    Render individual personalized exercise recommendation card.
    """
    title = exercise.get("exercise", "Drill")
    target = exercise.get("target", "Fitness")
    sets = exercise.get("sets", 3)
    duration = exercise.get("duration", "30 seconds")
    difficulty = exercise.get("difficulty", "Beginner")
    reason = exercise.get("reason", "Improves biomechanical movement.")
    
    diff_color = "#10B981" if difficulty.lower() == "beginner" else "#F59E0B" if difficulty.lower() == "intermediate" else "#EF4444"
    
    st.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #06B6D4; border-radius: 14px; padding: 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div>
                    <span style="font-size: 0.75rem; color: #06B6D4; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">TARGET: {target}</span>
                    <h4 style="margin: 4px 0 0 0; color: #FFFFFF; font-size: 1.1rem; font-weight: 800;">{title}</h4>
                </div>
                <span style="background: rgba(255, 255, 255, 0.05); color: {diff_color}; border: 1px solid {diff_color}; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700;">
                    {difficulty}
                </span>
            </div>
            
            <div style="display: flex; gap: 16px; margin: 12px 0; background: rgba(30, 41, 59, 0.5); padding: 10px 14px; border-radius: 8px;">
                <div>
                    <span style="font-size: 0.75rem; color: #94A3B8;">Prescription:</span>
                    <div style="font-weight: 700; color: #F8FAFC; font-size: 0.9rem;">{sets} sets × {duration}</div>
                </div>
            </div>
            
            <div style="font-size: 0.85rem; color: #CBD5E1; line-height: 1.4;">
                <strong style="color: #94A3B8;">Why:</strong> {reason}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_strengths_and_improvements(strengths, areas_to_improve):
    """Render side-by-side cards for Strengths and Areas to Improve."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            """
            <div style="margin-bottom: 12px;">
                <h4 style="color: #10B981; margin: 0; font-size: 1.1rem; font-weight: 800; display: flex; align-items: center; gap: 8px;">
                    ✅ YOUR STRENGTHS
                </h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        for s in strengths:
            st.markdown(
                f"""
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; color: #E2E8F0; font-size: 0.9rem; font-weight: 600;">
                    ✓ {s}
                </div>
                """,
                unsafe_allow_html=True
            )
            
    with col2:
        st.markdown(
            """
            <div style="margin-bottom: 12px;">
                <h4 style="color: #F59E0B; margin: 0; font-size: 1.1rem; font-weight: 800; display: flex; align-items: center; gap: 8px;">
                    ⚠️ AREAS TO IMPROVE
                </h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        for item in areas_to_improve:
            area_name = item.get("area", "Mobility")
            score = item.get("score", 65)
            priority = item.get("priority", "High")
            explanation = item.get("explanation", "Needs focus.")
            
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <strong style="color: #F8FAFC; font-size: 0.95rem;">⚠️ {area_name}</strong>
                        <span style="background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid #EF4444; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 700;">
                            {priority} Priority
                        </span>
                    </div>
                    <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 4px;">
                        {explanation} (Current Score: <strong style="color: #F59E0B;">{score}/100</strong>)
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
