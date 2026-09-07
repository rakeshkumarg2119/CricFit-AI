import plotly.graph_objects as go
import pandas as pd
import streamlit as st


# ─── Colour helpers ──────────────────────────────────────────────────────────
def _score_color(score):
    if score >= 80: return "#10B981"   # Emerald
    if score >= 70: return "#06B6D4"   # Cyan
    if score >= 60: return "#F59E0B"   # Amber
    return "#EF4444"                   # Red


def _safe_plotly_chart(fig):
    """Render a Plotly chart, suppressing any rendering errors."""
    try:
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    except TypeError:
        # Fallback for older Streamlit that still uses use_container_width
        try:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except Exception:
            st.warning("Chart rendering unavailable.")
    except Exception:
        st.warning("Chart rendering unavailable.")


# ─── Radar Chart ─────────────────────────────────────────────────────────────
def render_radar_chart(metrics):
    """Dark-themed Plotly radar chart with real player scores."""
    cats = ['Balance', 'Lower Stability', 'Hip Mobility',
            'Core Stability', 'Coordination', 'Body Symmetry']
    vals = [
        metrics.get("balance", 0),
        metrics.get("lower_body_stability", 0),
        metrics.get("hip_mobility", 0),
        metrics.get("core_stability", 0),
        metrics.get("coordination", 0),
        metrics.get("body_symmetry", 0),
    ]

    # close the loops
    cats_c = cats + [cats[0]]
    vals_c = vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_c, theta=cats_c, fill='toself', name='Your Biomechanics',
        fillcolor='rgba(6,182,212,0.22)',
        line=dict(color='#06B6D4', width=2.5),
        marker=dict(size=7, color='#38BDF8',
                    line=dict(color='#FFFFFF', width=1.5))
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickvals=[25, 50, 75, 100],
                tickfont=dict(size=9, color='#64748B'),
                gridcolor='rgba(255,255,255,0.08)',
                linecolor='rgba(255,255,255,0.08)',
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color='#CBD5E1'),
                gridcolor='rgba(255,255,255,0.07)',
                linecolor='rgba(255,255,255,0.07)',
            ),
            bgcolor='rgba(0,0,0,0)',
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            orientation='h', x=0.5, xanchor='center', y=-0.08,
            font=dict(color='#94A3B8', size=11),
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=20, r=20, t=20, b=20),
        height=300,
    )

    _safe_plotly_chart(fig)


# ─── Horizontal Bar Chart ─────────────────────────────────────────────────────
def render_horizontal_bar_chart(metrics):
    """Compact horizontal bar chart comparing all movement metrics at a glance."""
    labels = ['Balance', 'Lower Body Stability', 'Hip Mobility',
              'Core Stability', 'Coordination', 'Body Symmetry', 'Movement Quality']
    keys   = ['balance', 'lower_body_stability', 'hip_mobility',
              'core_stability', 'coordination', 'body_symmetry', 'movement_quality']
    values = [metrics.get(k, 0) for k in keys]
    colors = [_score_color(v) for v in values]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker=dict(
            color=colors,
            opacity=0.85,
            line=dict(color='rgba(0,0,0,0)', width=0),
        ),
        text=[f'<b>{v}</b>' for v in values],
        textposition='inside',
        textfont=dict(color='#FFFFFF', size=12, family='Plus Jakarta Sans'),
        hovertemplate='%{y}: <b>%{x}/100</b><extra></extra>',
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15,23,42,0.5)',
        font=dict(color='#94A3B8', family='Plus Jakarta Sans'),
        xaxis=dict(
            range=[0, 105], showgrid=True,
            gridcolor='rgba(255,255,255,0.06)',
            tickvals=[0, 25, 50, 75, 100],
            tickfont=dict(color='#64748B', size=10),
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(color='#E2E8F0', size=11),
            autorange='reversed',
        ),
        margin=dict(l=10, r=10, t=10, b=10),
        height=240,
        bargap=0.35,
    )

    _safe_plotly_chart(fig)


# ─── Progress Line Chart ──────────────────────────────────────────────────────
def render_progress_line_chart(history_reports):
    """Historical fitness progression line chart over multiple real analyses."""
    if not history_reports:
        return

    data = []
    for idx, report in enumerate(reversed(history_reports)):
        data.append({
            "Session": f"#{idx+1} {report.get('activity','').title()}",
            "Overall Fitness":  report.get("overall_score", 0),
            "Movement Quality": report.get("movement_quality", 0),
            "Balance":          report.get("metrics", {}).get("balance", 0),
            "Mobility":         report.get("metrics", {}).get("hip_mobility", 0),
            "Stability":        report.get("metrics", {}).get("lower_body_stability", 0),
        })

    df = pd.DataFrame(data)

    traces = [
        ("Overall Fitness",  "#06B6D4", "solid",  3, 9),
        ("Movement Quality", "#10B981", "dash",   2, 7),
        ("Balance",          "#8B5CF6", "solid",  2, 6),
        ("Mobility",         "#F59E0B", "dot",    2, 6),
        ("Stability",        "#EF4444", "dot",    2, 6),
    ]

    fig = go.Figure()
    for col, color, dash, width, msize in traces:
        fig.add_trace(go.Scatter(
            x=df["Session"], y=df[col],
            mode='lines+markers', name=col,
            line=dict(color=color, width=width, dash=dash),
            marker=dict(size=msize, color=color,
                        line=dict(color='#0B0F19', width=2)),
            hovertemplate=f'<b>{col}</b>: %{{y}}/100<extra></extra>',
        ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15,23,42,0.55)',
        font=dict(color='#94A3B8', family='Plus Jakarta Sans'),
        xaxis=dict(
            showgrid=True, gridcolor='rgba(255,255,255,0.05)',
            tickfont=dict(color='#E2E8F0', size=11),
            linecolor='rgba(255,255,255,0.08)',
        ),
        yaxis=dict(
            range=[0, 105], showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            tickfont=dict(color='#E2E8F0', size=11),
            title=dict(text='Score / 100', font=dict(color='#64748B', size=11)),
            zeroline=False,
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            font=dict(color='#CBD5E1', size=11),
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        height=380,
        hovermode='x unified',
    )

    _safe_plotly_chart(fig)
