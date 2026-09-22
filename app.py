"""
app.py  Amazon Seller Copilot, Streamlit UI.

PART A of Phase 5: foundation, theming, and the Signal Dashboard tab
(SYNTHETIC data  the 3 deterministic detectors from Phase 4). Market
Intelligence (LIVE agents), Decision Trace, the approval gate, and the
3D CUBE hero all come in Part B  placeholder tabs below mark exactly
where.

Run from the project root: `streamlit run app.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "db"))
sys.path.insert(0, str(PROJECT_ROOT / "signals"))
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

import streamlit as st
import plotly.graph_objects as go

import db
from inventory_signal import run_inventory_signal_for_all_products
from ppc_waste_signal import run_ppc_waste_signal_for_all_products
from rank_bb_signal import run_rank_bb_signal_for_all_products
from ui.theme import inject_custom_css, severity_badge_html, COLORS

st.set_page_config(
    page_title="Amazon Seller Copilot",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_custom_css()
db.init_db()


def render_hero() -> None:
    st.markdown(
        """
        <div class="scp-hero">
            <div class="scp-eyebrow">SYDON-1  CUBE BUILDATHON PRACTICE PROJECT</div>
            <div class="scp-title">Amazon Seller Copilot</div>
            <div class="scp-subtitle">Signals become intelligence. Intelligence becomes an
            action a human still has to approve.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str) -> str:
    return f"""
    <div class="scp-metric">
        <div class="scp-metric-value">{value}</div>
        <div class="scp-metric-label">{label}</div>
    </div>
    """


def get_latest_signal_for_product(product_id: str) -> dict | None:
    signals = db.get_detected_signals(product_id)
    return dict(signals[0]) if signals else None


def render_signal_dashboard_tab() -> None:
    st.markdown(
        '<span class="scp-badge scp-badge-fake">Synthetic data  demo only, no live calls</span>',
        unsafe_allow_html=True,
    )
    st.write("")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔍 Run signal detection", use_container_width=True):
            with st.spinner("Scanning products against all three detectors..."):
                db.clear_detected_signals()
                n1 = run_inventory_signal_for_all_products()
                n2 = run_ppc_waste_signal_for_all_products()
                n3 = run_rank_bb_signal_for_all_products()
            st.success(f"Detection complete  {n1 + n2 + n3} signal(s) flagged.")
            st.rerun()

    products = db.get_products()
    all_signals = db.get_detected_signals()
    flagged_ids = {s["product_id"] for s in all_signals}
    high_severity_ids = {s["product_id"] for s in all_signals if s["severity"] == "high"}

    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.markdown(render_metric("Total Products", str(len(products))), unsafe_allow_html=True)
    with metric_cols[1]:
        st.markdown(render_metric("Flagged", str(len(flagged_ids))), unsafe_allow_html=True)
    with metric_cols[2]:
        st.markdown(render_metric("High Severity", str(len(high_severity_ids))), unsafe_allow_html=True)
    with metric_cols[3]:
        coverage = f"{round(100 * len(flagged_ids) / max(1, len(products)))}%"
        st.markdown(render_metric("Flag Rate", coverage), unsafe_allow_html=True)

    st.write("")
    st.write("")

    if not products:
        st.info("No products yet. Run `python data/generate_synthetic_data.py` from the project root first.")
        return

    left, right = st.columns([1, 2])

    with left:
        st.markdown("##### Products")
        product_labels = []
        product_map = {}
        for p in products:
            latest_signal = get_latest_signal_for_product(p["product_id"])
            severity = latest_signal["severity"] if latest_signal else None
            badge = severity_badge_html(severity)
            label = f"{p['name']}"
            product_labels.append(label)
            product_map[label] = p["product_id"]
            st.markdown(
                f'<div class="scp-card">{badge}<br><b>{p["name"]}</b>'
                f'<br><span style="color:{COLORS["text_muted"]};font-size:0.8rem;">'
                f'{p["category"]}  ${p["base_price"]:.2f}</span></div>',
                unsafe_allow_html=True,
            )

        selected_label = st.selectbox("Inspect a product", product_labels)
        selected_id = product_map[selected_label]

    with right:
        render_product_detail(selected_id)


def render_product_detail(product_id: str) -> None:
    rows = db.get_metrics_for_product(product_id)
    if not rows:
        st.warning("No metrics found for this product.")
        return

    dates = [r["date"] for r in rows]
    ranks = [r["rank"] for r in rows]
    inventory = [r["inventory_level"] for r in rows]
    acos = [(r["ad_spend"] / r["ad_sales"]) if r["ad_sales"] > 0 else None for r in rows]

    signal = get_latest_signal_for_product(product_id)
    if signal:
        st.markdown(
            f'<div class="scp-card" style="border-left:4px solid {COLORS["amber"]};">'
            f'<b> {signal["signal_type"].replace("_", " ").title()} detected</b> '
            f'{severity_badge_html(signal["severity"])}'
            f'<br><span style="color:{COLORS["text_muted"]};font-size:0.85rem;">'
            f'As of {signal["date"]}</span></div>',
            unsafe_allow_html=True,
        )
        with st.expander("View evidence"):
            st.json(json.loads(signal["evidence"]))
    else:
        st.markdown(
            f'<div class="scp-card" style="border-left:4px solid {COLORS["green"]};">'
            f'<b> No signals detected</b>  this product looks healthy.</div>',
            unsafe_allow_html=True,
        )

    fig_rank = go.Figure()
    fig_rank.add_trace(
        go.Scatter(
            x=dates, y=ranks, mode="lines", name="Rank",
            line=dict(color=COLORS["blue"], width=2),
            fill="tozeroy", fillcolor="rgba(79, 195, 247, 0.08)",
        )
    )
    fig_rank.update_layout(
        title="Sales Rank (lower is better)",
        yaxis=dict(autorange="reversed"),
        template="plotly_dark",
        paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
        height=260, margin=dict(l=40, r=20, t=40, b=30),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig_inv = go.Figure()
        fig_inv.add_trace(
            go.Scatter(x=dates, y=inventory, mode="lines", name="Inventory",
                       line=dict(color=COLORS["amber"], width=2),
                       fill="tozeroy", fillcolor="rgba(232, 163, 61, 0.1)")
        )
        fig_inv.update_layout(
            title="Inventory Level", template="plotly_dark",
            paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
            height=240, margin=dict(l=40, r=20, t=40, b=30),
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with c2:
        fig_acos = go.Figure()
        fig_acos.add_trace(
            go.Scatter(x=dates, y=acos, mode="lines", name="ACOS",
                       line=dict(color=COLORS["red"], width=2))
        )
        fig_acos.add_hline(y=0.40, line_dash="dash", line_color=COLORS["text_muted"],
                            annotation_text="40% threshold")
        fig_acos.update_layout(
            title="ACOS (ad spend / ad sales)", template="plotly_dark",
            paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
            height=240, margin=dict(l=40, r=20, t=40, b=30), yaxis_tickformat=".0%",
        )
        st.plotly_chart(fig_acos, use_container_width=True)


def render_placeholder_tab(title: str) -> None:
    st.markdown(
        f'<div class="scp-card" style="text-align:center; padding:3rem;">'
        f'<h4 style="color:{COLORS["text_muted"]};">{title}</h4>'
        f'<p style="color:{COLORS["text_muted"]};">Built in Phase 5  Part B.</p></div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    render_hero()
    tab1, tab2, tab3 = st.tabs(["📊 Signal Dashboard", "🌐 Market Intelligence", "🧭 Decision Trace"])
    with tab1:
        render_signal_dashboard_tab()
    with tab2:
        render_placeholder_tab("Market Intelligence (Live Agents)")
    with tab3:
        render_placeholder_tab("Decision Trace")


if __name__ == "__main__":
    main()
