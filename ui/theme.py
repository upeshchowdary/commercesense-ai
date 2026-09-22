"""
theme.py  centralized visual identity for the Streamlit UI, matching
the CUBE Buildathon / Sydon AI visual language taken directly from the
buildathon's own presentation deck: near-black background, amber
accent, blue-cyan gradient, dark card panels with subtle borders,
italic muted taglines. Import inject_custom_css() once, at the very
top of app.py, before anything else renders.

Deliberately CSS-only for cards/metrics/badges  no JS-driven counters
or interactions here. Streamlit's components.html() runs in a
sandboxed iframe with no reliable two-way binding back to Streamlit's
own state, so anything that needs real interactivity (buttons,
selection) stays as native Streamlit widgets styled via CSS, not
custom JS. The one deliberate exception (a real 3D CSS cube, no JS
state needed) comes in Part B.
"""

from __future__ import annotations

import streamlit as st

COLORS = {
    "bg": "#0B0E14",
    "panel": "#131722",
    "panel_border": "#232838",
    "text": "#E8EAF0",
    "text_muted": "#8B93A7",
    "amber": "#E8A33D",
    "blue": "#4FC3F7",
    "blue_deep": "#2E86FF",
    "green": "#3ECF8E",
    "red": "#FF6B6B",
    "yellow": "#F0C674",
}

SEVERITY_COLORS = {
    "high": COLORS["red"],
    "medium": COLORS["amber"],
    "low": COLORS["yellow"],
    None: COLORS["text_muted"],
}

CONFIDENCE_COLORS = {
    "high": COLORS["green"],
    "medium": COLORS["amber"],
    "low": COLORS["yellow"],
    "none": COLORS["text_muted"],
}


def inject_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {COLORS["bg"]};
            color: {COLORS["text"]};
        }}
        [data-testid="stSidebar"] {{
            background: {COLORS["panel"]};
            border-right: 1px solid {COLORS["panel_border"]};
        }}
        .scp-hero {{
            padding: 1.5rem 2rem;
            border-radius: 16px;
            background: linear-gradient(135deg, {COLORS["panel"]} 0%, #0F1420 100%);
            border: 1px solid {COLORS["panel_border"]};
            margin-bottom: 1.5rem;
            animation: scp-fade-in 0.6s ease-out;
        }}
        .scp-eyebrow {{
            color: {COLORS["amber"]};
            font-size: 0.8rem;
            letter-spacing: 0.15em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .scp-title {{
            font-size: 2.1rem;
            font-weight: 700;
            margin: 0.2rem 0 0.4rem 0;
            background: linear-gradient(90deg, {COLORS["blue"]}, {COLORS["blue_deep"]});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .scp-subtitle {{
            color: {COLORS["text_muted"]};
            font-style: italic;
            font-size: 0.95rem;
        }}
        .scp-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .scp-badge-fake {{
            background: rgba(139, 147, 167, 0.15);
            color: {COLORS["text_muted"]};
            border: 1px solid {COLORS["panel_border"]};
        }}
        .scp-badge-live {{
            background: rgba(79, 195, 247, 0.12);
            color: {COLORS["blue"]};
            border: 1px solid rgba(79, 195, 247, 0.35);
        }}
        .scp-card {{
            background: {COLORS["panel"]};
            border: 1px solid {COLORS["panel_border"]};
            border-radius: 12px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.75rem;
            transition: border-color 0.2s ease, transform 0.2s ease;
            animation: scp-slide-up 0.4s ease-out;
        }}
        .scp-card:hover {{
            border-color: {COLORS["amber"]};
            transform: translateY(-2px);
        }}
        .scp-metric {{
            background: {COLORS["panel"]};
            border: 1px solid {COLORS["panel_border"]};
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            animation: scp-fade-in 0.5s ease-out;
        }}
        .scp-metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {COLORS["blue"]};
        }}
        .scp-metric-label {{
            color: {COLORS["text_muted"]};
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        @keyframes scp-fade-in {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        @keyframes scp-slide-up {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def severity_badge_html(severity: str | None) -> str:
    color = SEVERITY_COLORS.get(severity, COLORS["text_muted"])
    label = severity.upper() if severity else "HEALTHY"
    return (
        f'<span style="color:{color}; font-weight:700; font-size:0.75rem; '
        f'letter-spacing:0.05em;"> {label}</span>'
    )


def confidence_badge_html(confidence: str) -> str:
    color = CONFIDENCE_COLORS.get(confidence, COLORS["text_muted"])
    return (
        f'<span style="background:{color}22; color:{color}; padding:0.15rem 0.6rem; '
        f'border-radius:999px; font-size:0.7rem; font-weight:700; text-transform:uppercase; '
        f'letter-spacing:0.05em;">{confidence}</span>'
    )
