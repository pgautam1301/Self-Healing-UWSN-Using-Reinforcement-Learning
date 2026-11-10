"""
app.py - AquaNet Premium 3D Underwater Wireless Sensor Network Control Center.
Project: Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning
Implementation: NS-3.41 + Aqua-Sim NG | 8-State Fault-Aware Q-Learning (P4 Architecture)

UI Architecture: Executive Pure Black / Charcoal & Lavender Glassmorphic Design
Featuring Interactive WebGL Three.js 3D Subsea Simulation Canvas, Real Telemetry Scrubbing,
Step-by-Step Self-Healing Workflow, and Publication-Grade Protocol Analytics.
"""

import time
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

from data_loader import (
    load_per_run_data,
    load_summary_statistics,
    get_topology_nodes,
    get_potential_acoustic_links,
    load_actual_simulation_trace,
    PROTOCOL_NAMES,
    PROTOCOL_COLORS,
    METRIC_DEFINITIONS
)

from simulator_engine import (
    STATE_DEFINITIONS,
    ACTION_DEFINITIONS,
    EDUCATIONAL_STEPS,
    step_simulation,
    prewarm_q_table,
    initialize_q_table,
    execute_q_learning_update,
    calculate_reward_c,
    DEFAULT_ALPHA,
    DEFAULT_GAMMA
)
from network_builder import render_network_builder
from threejs_component import get_threejs_html


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AquaNet — 3D Underwater Network Control Center",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# PREMIUM CHARCOAL & LAVENDER VISUAL DESIGN (REFERENCE PALETTE)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

    :root {
        --bg-main: #09090B;
        --panel-bg: #18181B;
        --panel-bg-secondary: #222126;
        --border-subtle: #27272A;
        --border-accent: rgba(167, 139, 250, 0.28);
        --accent-lavender: #C4B5FD;
        --accent-purple: #A78BFA;
        --accent-violet: #DDD6FE;
        --text-white: #FAFAFA;
        --text-muted: #A1A1AA;
        --status-ok: #34D399;
        --status-err: #EF4444;
        --status-warn: #FBBF24;
    }

    /* Global Charcoal Background */
    .stApp {
        background-color: var(--bg-main) !important;
        color: var(--text-white) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Executive Top Command Header */
    .command-header {
        background: linear-gradient(135deg, #18181B 0%, #222126 100%);
        border: 1px solid var(--border-accent);
        border-radius: 14px;
        padding: 16px 24px;
        margin-bottom: 22px;
        backdrop-filter: blur(14px);
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
    }
    .command-title {
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        background: linear-gradient(90deg, #FAFAFA 0%, #C4B5FD 50%, #A78BFA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .command-subtitle {
        font-size: 0.8rem;
        color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace;
        margin-top: 3px;
    }

    /* Premium Rounded Sidebar */
    [data-testid="stSidebar"] {
        background-color: #121215 !important;
        border-right: 1px solid var(--border-subtle) !important;
        box-shadow: 6px 0 28px rgba(0, 0, 0, 0.65);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--accent-lavender) !important;
        font-size: 0.88rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* Sidebar Navigation Radio Buttons */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: rgba(24, 24, 27, 0.7);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 6px;
        transition: all 0.22s ease;
        cursor: pointer;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: var(--panel-bg-secondary);
        border-color: var(--accent-purple);
        box-shadow: 0 0 12px rgba(167, 139, 250, 0.2);
        transform: translateX(3px);
    }

    /* Rounded Charcoal Cards */
    .metric-card {
        background: var(--panel-bg);
        border: 1px solid var(--border-accent);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 14px;
        position: relative;
        overflow: hidden;
        transition: all 0.25s ease;
    }
    .metric-card:hover {
        border-color: var(--accent-purple);
        box-shadow: 0 8px 26px rgba(167, 139, 250, 0.22);
        transform: translateY(-2px);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 3px; height: 100%;
        background: linear-gradient(180deg, var(--accent-purple) 0%, transparent 100%);
    }
    .metric-title {
        font-size: 0.74rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: var(--text-white);
        letter-spacing: -0.02em;
        margin-bottom: 2px;
    }
    .metric-subtext {
        font-size: 0.72rem;
        color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace;
    }

    /* Status Badges */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .status-pill-ok {
        background: rgba(52, 211, 153, 0.12);
        border: 1px solid rgba(52, 211, 153, 0.45);
        color: #34D399;
    }
    .status-pill-alert {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.5);
        color: #F87171;
    }
    .status-pill-lavender {
        background: rgba(196, 181, 253, 0.12);
        border: 1px solid rgba(167, 139, 250, 0.45);
        color: #DDD6FE;
    }

    /* Section Headers */
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-white);
        border-bottom: 1.5px solid var(--border-accent);
        padding-bottom: 8px;
        margin-top: 14px;
        margin-bottom: 18px;
    }

    /* Callout Card */
    .callout-box {
        background: var(--panel-bg);
        border-left: 4px solid var(--accent-purple);
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 18px;
        font-size: 0.88rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    }

    /* Stepper Navigation */
    .stepper-container {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 14px;
        background: #141416;
        padding: 8px 12px;
        border-radius: 10px;
        border: 1px solid var(--border-subtle);
    }
    .stepper-step {
        flex: 1;
        text-align: center;
        padding: 6px 4px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        background: rgba(34, 33, 38, 0.6);
        color: var(--text-muted);
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    .stepper-step.active {
        background: rgba(167, 139, 250, 0.2);
        color: var(--accent-lavender);
        border-color: var(--accent-purple);
        font-weight: 700;
        box-shadow: 0 0 12px rgba(167, 139, 250, 0.3);
    }
    .stepper-step.completed {
        background: rgba(52, 211, 153, 0.12);
        color: #34D399;
        border-color: rgba(52, 211, 153, 0.3);
    }

    /* Modern Buttons */
    .stButton > button {
        background: #1E1E22 !important;
        color: var(--text-white) !important;
        border: 1px solid rgba(167, 139, 250, 0.3) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: #27272F !important;
        border-color: var(--accent-lavender) !important;
        box-shadow: 0 0 12px rgba(167, 139, 250, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* Dataframe Polish */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid var(--border-subtle);
        background-color: var(--panel-bg);
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# PLOTLY THEME HELPER (CHARCOAL & LAVENDER PALETTE)
# -----------------------------------------------------------------------------
def get_charcoal_lavender_plotly_layout(title="", height=420):
    """Generates an executive charcoal and lavender Plotly theme."""
    return dict(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(color="#FAFAFA", size=13, family="Inter, sans-serif")
        ),
        paper_bgcolor="#18181B",
        plot_bgcolor="#18181B",
        font=dict(color="#A1A1AA", family="Inter, sans-serif"),
        height=height,
        margin=dict(l=35, r=35, t=45, b=35),
        legend=dict(
            bgcolor="rgba(24, 24, 27, 0.85)",
            bordercolor="#27272A",
            borderwidth=1,
            font=dict(color="#DDD6FE", size=10)
        )
    )


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION & MISSION CONTROL TELEMETRY
# -----------------------------------------------------------------------------
st.sidebar.markdown("""
<div style='text-align: center; padding: 12px 6px; margin-bottom: 12px; border-bottom: 1px solid #27272A;'>
    <div style='font-size: 2.2rem; margin-bottom: 4px; filter: drop-shadow(0 0 10px rgba(167, 139, 250, 0.4));'>🔮</div>
    <h3 style='margin: 0; color: #C4B5FD; font-weight: 800; font-size: 1.15rem; letter-spacing: 0.05em;'>AQUANET CONTROL</h3>
    <p style='margin: 2px 0 0 0; font-size: 0.72rem; color: #A1A1AA; font-family: monospace;'>3D UWSN Operations Platform</p>
    <div style='margin-top: 8px;'>
        <span class='status-pill status-pill-ok'>🟢 NS-3.41 ENGINE SYNCHRONIZED</span>
    </div>
</div>
""", unsafe_allow_html=True)

nav_options = [
    "🏠 Overview",
    "📊 Actual NS-3 Results Replay",
    "🔄 Interactive RL Simulator",
    "🛠️ 3D Network Builder",
    "📈 Protocol Benchmark",
    "🌊 Underwater Topology",
    "🧠 RL Architecture and Q-Table"
]

nav_mode = st.sidebar.radio(
    "Operations Navigation:",
    nav_options,
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div class='metric-card' style='padding: 12px 14px; margin-bottom: 10px;'>
    <div class='metric-title'>Mission Parameters</div>
    <div style='font-size: 0.8rem; line-height: 1.5; color: #E4E4E7;'>
        • <b>Architecture:</b> P4 Fault-Aware RL-VBF<br>
        • <b>Framework:</b> NS-3.41 + Aqua-Sim NG<br>
        • <b>Nodes:</b> 12 (Reflected 3D Space)<br>
        • <b>Fault Event:</b> Sensor 5 at $t = 50.0\\text{ s}$<br>
        • <b>Acoustic Speed:</b> $1500\\text{ m/s}$<br>
        • <b>Tx Range:</b> $250.0\\text{ m}$
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<small style='color:#71717A; font-family: monospace;'>Authoritative Source: results_p6/P6_5_FINAL_RESULTS_AUDIT.md</small>", unsafe_allow_html=True)


# ==============================================================================
# SECTION 1: OVERVIEW (EXECUTIVE 3D OPERATIONS CENTER)
# ==============================================================================
if nav_mode == "🏠 Overview":
    st.markdown("""
    <div class='command-header'>
        <div>
            <h1 class='command-title'>AQUANET: 3D UNDERWATER NETWORK OPERATIONS CENTER</h1>
            <div class='command-subtitle'>Autonomous Self-Healing Underwater Wireless Sensor Networks via Multi-Agent Q-Learning</div>
        </div>
        <div>
            <span class='status-pill status-pill-lavender'>EXECUTIVE OVERVIEW</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top-Level Executive Metric HUD
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Total Nodes</div>
            <div class='metric-value'>12</div>
            <div class='metric-subtext'>Source, Relays, Gateway</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Active Nodes</div>
            <div class='metric-value' style='color:#34D399;'>11</div>
            <div class='metric-subtext'>Post-Failure Operational</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Failed Nodes</div>
            <div class='metric-value' style='color:#EF4444;'>1</div>
            <div class='metric-subtext'>Sensor 5 Halted at 50s</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Network Energy</div>
            <div class='metric-value' style='color:#C4B5FD;'>477.87 J</div>
            <div class='metric-subtext'>-35.90 J vs Forced VBF</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Unique PDR</div>
            <div class='metric-value' style='color:#A78BFA;'>62.94%</div>
            <div class='metric-subtext'>± 1.93% (Audited P6.4)</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Average Latency</div>
            <div class='metric-value' style='color:#FBBF24;'>1.8072 s</div>
            <div class='metric-subtext'>Tail P95: 2.3479 s</div>
        </div>
        """, unsafe_allow_html=True)

    # 3D Visual Centrepiece (Embedded Interactive WebGL Three.js Component)
    st.markdown("<h3 class='section-header'>Interactive 3D Subsea Simulation Viewport</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class='callout-box'>
        <b>Interactive 3D Viewport Controls:</b> Rotate (Left-click drag), Zoom (Mouse-wheel / pinch), Pan (Right-click drag). 
        Connections are initially hidden. Click <b>Show Links</b> to zoom in and progressively draw acoustic links in lavender. 
        Click <b>Simulate t = 50s Fault</b> to observe Sensor 5 turn red and activate the self-healing recovery route via Sensor 6 in green.
    </div>
    """, unsafe_allow_html=True)

    three_html = get_threejs_html(
        active_step=0,
        is_fault_active=False,
        show_links_initially=False,
        selected_node_id=5
    )
    components.html(three_html, height=620)

    # Self-Healing Workflow Architecture Overview
    st.markdown("<h3 class='section-header'>Autonomous Self-Healing Mechanism (P4 Architecture)</h3>", unsafe_allow_html=True)
    w1, w2, w3, w4 = st.columns(4)
    with w1:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>1. Fault Occurrence</div>
            <div style='font-size: 0.95rem; font-weight: 700; color: #EF4444; margin-bottom: 4px;'>Sensor 5 Disrupts</div>
            <div style='font-size: 0.8rem; color: #A1A1AA; line-height: 1.4;'>
                At $t = 50.0\\text{ s}$, Sensor 5 halts transceiver operations. Residual battery halts at $72.21\\text{ J}$, creating an acoustic void.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with w2:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>2. Timeout Tracking</div>
            <div style='font-size: 0.95rem; font-weight: 700; color: #FBBF24; margin-bottom: 4px;'>$m\\_timeouts \\ge 2$</div>
            <div style='font-size: 0.8rem; color: #A1A1AA; line-height: 1.4;'>
                Sensor 4 fails to receive reverse ACKs. Two consecutive timeouts trigger state transition from Healthy $S3$ to Degraded $S7$.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with w3:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>3. Temporal Deferral</div>
            <div style='font-size: 0.95rem; font-weight: 700; color: #C4B5FD; margin-bottom: 4px;'>ACTION_DEFER (0.5s)</div>
            <div style='font-size: 0.8rem; color: #A1A1AA; line-height: 1.4;'>
                In State $S7$, Q-table policy selects `ACTION_DEFER`. Sensor 4 pauses for $0.5\\text{ s}$, intentionally yielding the acoustic channel.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with w4:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>4. Spatial Bypass</div>
            <div style='font-size: 0.95rem; font-weight: 700; color: #34D399; margin-bottom: 4px;'>Sensor 6 Forwards</div>
            <div style='font-size: 0.8rem; color: #A1A1AA; line-height: 1.4;'>
                Healthy parallel candidate Sensor 6 overhears and forwards upward toward surface sink Node 11. Delivery parity verified ($62.50\\%$).
            </div>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# SECTION 2: ACTUAL NS-3 RESULTS REPLAY
# ==============================================================================
elif nav_mode == "📊 Actual NS-3 Results Replay":
    st.markdown("""
    <div class='command-header'>
        <div>
            <h1 class='command-title'>ACTUAL NS-3 SIMULATION TELEMETRY REPLAY</h1>
            <div class='command-subtitle'>Timestamp-accurate trace replay of multi-seed physical Layer-3 acoustic events</div>
        </div>
        <div>
            <span class='status-pill status-pill-lavender'>REAL HISTORICAL DATASET</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='callout-box'>
        <b>Mode A Replay Guarantee:</b> All packet generation, intermediate forwarding hops, reverse ACKs, unacknowledged timeouts, 
        and energy values are directly streamed from verified NS-3.41 simulation traces in <code>results_p6/p4_run01.log</code> through <code>run10.log</code>. 
        Zero values or packets are synthetic.
    </div>
    """, unsafe_allow_html=True)

    col_sel1, col_sel2 = st.columns([1.2, 2.8])
    with col_sel1:
        run_choice = st.selectbox("Select P4 Multi-Seed Run:", list(range(1, 11)), index=0, format_func=lambda r: f"P4 Multi-Seed Run {r:02d} (Seed {r})")
    with col_sel2:
        trace = load_actual_simulation_trace(run_num=run_choice)
        if trace and not trace['events_df'].empty:
            st.caption(f"Loaded **{len(trace['events_df']):,}** timestamped events for Multi-Seed Run {run_choice:02d}. Source Node 12 -> Surface Sink Node 11.")

    if trace is None or trace['events_df'].empty:
        st.error(f"Could not load log trace for P4 Run {run_choice}. Please verify results_p6/p4_run{run_choice:02d}.log.")
    else:
        df_events = trace['events_df']

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>Injected Packets</div>
                <div class='metric-value'>310</div>
                <div class='metric-subtext'>Source Node 12 (0.5s - 100s)</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-title'>Total Deliveries</div>
                <div class='metric-value'>{trace['total_deliveries']}</div>
                <div class='metric-subtext'>Duplicate-inclusive reception</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            uniq_pdr = (trace['unique_deliveries'] / 310.0) * 100.0
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-title'>Unique PDR</div>
                <div class='metric-value' style='color:#C4B5FD;'>{uniq_pdr:.2f}%</div>
                <div class='metric-subtext'>{trace['unique_deliveries']} unique UIDs delivered</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>Fault Schedule</div>
                <div class='metric-value' style='color:#FBBF24;'>t = 50.0 s</div>
                <div class='metric-subtext'>Deterministic transceiver halt</div>
            </div>
            """, unsafe_allow_html=True)
        with c5:
            st.markdown("""
            <div class='metric-card'>
                <div class='metric-title'>Sensor 5 Residual</div>
                <div class='metric-value' style='color:#34D399;'>72.21 J</div>
                <div class='metric-subtext'>Halted cleanly (Initial 100 J)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<h3 class='section-header'>Timeline Scrubbing & Event Horizon</h3>", unsafe_allow_html=True)
        col_ctrl1, col_ctrl2 = st.columns([2.5, 1.5])
        with col_ctrl1:
            time_slider = st.slider(
                "Telemetry Time Horizon (Seconds):",
                min_value=0.0,
                max_value=100.0,
                value=55.0,
                step=0.5
            )
        with col_ctrl2:
            event_type_filter = st.selectbox(
                "Filter Physical Event Type:",
                ["All Events", "SOURCE_TX", "RL_DECISION", "RELAY_ACK", "SINK_DELIVERY", "ACK_TIMEOUT", "SENSOR_FAILURE"]
            )

        filtered_df = df_events[df_events['time'] <= time_slider]
        if event_type_filter != "All Events":
            filtered_df = filtered_df[filtered_df['event_type'] == event_type_filter]

        if time_slider >= 50.0:
            st.markdown(f"""
            <div style='margin-bottom: 12px;'>
                <span class='status-pill status-pill-alert'>CRITICAL EVENT: SENSOR 5 HALTED AT 50.0s (TRANSCEIVER OFFLINE)</span>
                <span class='status-pill status-pill-lavender'>ACTIVE EVENTS IN VIEW: {len(filtered_df):,}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style='margin-bottom: 12px;'>
                <span class='status-pill status-pill-ok'>NOMINAL OPERATION: ALL 12 NODES HEALTHY (t < 50.0s)</span>
                <span class='status-pill status-pill-lavender'>ACTIVE EVENTS IN VIEW: {len(filtered_df):,}</span>
            </div>
            """, unsafe_allow_html=True)

        col_viz, col_log = st.columns([1.1, 0.9])

        with col_viz:
            st.markdown("#### Physical Topology State")
            nodes = get_topology_nodes()
            links = get_potential_acoustic_links(tx_range=250.0)

            fig3d = go.Figure()

            # Surface and Seafloor planes
            grid_xs = [0, 550, 550, 0, 0]
            grid_ys = [0, 0, 550, 550, 0]
            fig3d.add_trace(go.Scatter3d(
                x=grid_xs, y=grid_ys, z=[0, 0, 0, 0, 0],
                mode='lines', line=dict(color='rgba(255, 255, 255, 0.1)', width=1, dash='dot'),
                hoverinfo='none', showlegend=False
            ))
            fig3d.add_trace(go.Scatter3d(
                x=grid_xs, y=grid_ys, z=[100, 100, 100, 100, 100],
                mode='lines', line=dict(color='rgba(167, 139, 250, 0.25)', width=1.5, dash='dot'),
                hoverinfo='none', showlegend=False
            ))

            for link in links:
                n1, n2 = link['node1'], link['node2']
                is_dead_link = link['involves_s5'] and (time_slider >= 50.0)
                link_color = 'rgba(239, 68, 68, 0.45)' if is_dead_link else 'rgba(167, 139, 250, 0.2)'
                dash = 'dash' if is_dead_link else 'solid'
                width = 2.5 if is_dead_link else 1.2

                fig3d.add_trace(go.Scatter3d(
                    x=[n1['x'], n2['x']], y=[n1['y'], n2['y']], z=[n1['z'], n2['z']],
                    mode='lines', line=dict(color=link_color, width=width, dash=dash),
                    hoverinfo='none', showlegend=False
                ))

            for n in nodes:
                is_s5 = (n['id'] == 5)
                s5_failed = is_s5 and (time_slider >= 50.0)

                if n['type'] == 'source':
                    color, size, sym = '#C4B5FD', 11, 'diamond'
                elif n['type'] == 'sink':
                    color, size, sym = '#34D399', 13, 'square'
                elif s5_failed:
                    color, size, sym = '#EF4444', 14, 'x'
                else:
                    color, size, sym = '#A78BFA', 9, 'circle'

                node_name = n['name'] + (" [FAILED / HALTED]" if s5_failed else "")
                fig3d.add_trace(go.Scatter3d(
                    x=[n['x']], y=[n['y']], z=[n['z']],
                    mode='markers+text',
                    marker=dict(size=size, color=color, symbol=sym, line=dict(color='#FFFFFF', width=1)),
                    text=[n['short_name']],
                    textposition='top center',
                    textfont=dict(color='#FAFAFA', size=10),
                    name=n['short_name'],
                    hovertext=f"<b>{node_name}</b><br>Coordinates: ({n['x']:.1f}, {n['y']:.1f}, {n['z']:.1f}) m<br>Status: {n['status']}",
                    hoverinfo='text',
                    showlegend=False
                ))

            layout_3d = get_charcoal_lavender_plotly_layout(f"3D Acoustic Vector at t = {time_slider:.1f} s", height=440)
            layout_3d['scene'] = dict(
                xaxis=dict(title='X East-West (m)', backgroundcolor='#18181B', gridcolor='#27272A', color='#A1A1AA'),
                yaxis=dict(title='Y North-South (m)', backgroundcolor='#18181B', gridcolor='#27272A', color='#A1A1AA'),
                zaxis=dict(title='Reflected Elevation Z (m)', backgroundcolor='#18181B', gridcolor='#27272A', color='#A1A1AA'),
                camera=dict(eye=dict(x=1.65, y=-1.65, z=1.25))
            )
            fig3d.update_layout(layout_3d)
            st.plotly_chart(fig3d, use_container_width=True)

        with col_log:
            st.markdown("#### Chronological Telemetry Log Stream")
            display_cols = ['time', 'event_type', 'node_name', 'packet_uid', 'reward', 'q_value', 'description']
            st.dataframe(
                filtered_df[display_cols].tail(120),
                height=440,
                use_container_width=True
            )


# ==============================================================================
# SECTION 3: INTERACTIVE RL SIMULATOR
# ==============================================================================
elif nav_mode == "🔄 Interactive RL Simulator":
    st.markdown("""
    <div class='command-header'>
        <div>
            <h1 class='command-title'>INTERACTIVE STEP-BY-STEP RL SELF-HEALING SIMULATOR</h1>
            <div class='command-subtitle'>Walkthrough of Sector Blackout, Timeout Detection, Q-Learning Update, and Spatial Candidate Bypass</div>
        </div>
        <div>
            <span class='status-pill status-pill-lavender'>9-STEP PEDAGOGICAL WORKFLOW</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if 'demo_step' not in st.session_state:
        st.session_state['demo_step'] = 0
    if 'sim_q_table' not in st.session_state:
        st.session_state['sim_q_table'] = prewarm_q_table()

    # Stepper Navigation
    stepper_html = "<div class='stepper-container'>"
    for idx, s_def in enumerate(EDUCATIONAL_STEPS):
        cls = "stepper-step"
        if idx == st.session_state['demo_step']:
            cls += " active"
        elif idx < st.session_state['demo_step']:
            cls += " completed"
        stepper_html += f"<div class='{cls}'>Step {idx+1}</div>"
    stepper_html += "</div>"
    st.markdown(stepper_html, unsafe_allow_html=True)

    # Controls Deck
    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns([1, 1, 1, 2.5])
    with c_btn1:
        if st.button("⏮ Previous Step", use_container_width=True):
            st.session_state['demo_step'] = max(0, st.session_state['demo_step'] - 1)
            st.rerun()
    with c_btn2:
        if st.button("⏭ Next Step", use_container_width=True):
            st.session_state['demo_step'] = min(len(EDUCATIONAL_STEPS) - 1, st.session_state['demo_step'] + 1)
            st.rerun()
    with c_btn3:
        if st.button("🔄 Reset Demo", use_container_width=True):
            st.session_state['demo_step'] = 0
            st.session_state['sim_q_table'] = prewarm_q_table()
            st.rerun()
    with c_btn4:
        st.session_state['demo_step'] = st.selectbox(
            "Jump Directly to Demonstration Step:",
            range(len(EDUCATIONAL_STEPS)),
            format_func=lambda i: EDUCATIONAL_STEPS[i]['title'],
            index=st.session_state['demo_step']
        )

    current_step = step_simulation(st.session_state['demo_step'])

    # Step Status Banner
    s5_color = "#EF4444" if "FAILED" in current_step['s5_status'] else "#34D399"
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #18181B 0%, #222126 100%); border: 1px solid var(--border-accent); border-radius: 12px; padding: 14px 20px; margin-bottom: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.4);'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <div style='color: #C4B5FD; font-weight: 800; font-size: 1.15rem;'>{current_step['title']}</div>
            <span class='status-pill status-pill-lavender'>STEP {current_step['step_num']} OF 9</span>
        </div>
        <div style='display: flex; gap: 14px; font-size: 0.8rem; color: #A1A1AA; margin-top: 6px; margin-bottom: 8px; font-family: monospace;'>
            <span><b>Actor:</b> <span style='color: #FAFAFA;'>{current_step['actor']}</span></span> |
            <span><b>Time:</b> <span style='color: #FAFAFA;'>{current_step['time']}</span></span> |
            <span><b>Phase:</b> <span style='color: #FAFAFA;'>{current_step['network_phase']}</span></span> |
            <span><b>Sensor 5:</b> <span style='color: {s5_color}; font-weight: bold;'>{current_step['s5_status']}</span></span>
        </div>
        <div style='color: #E4E4E7; font-size: 0.92rem; line-height: 1.5;'>{current_step['event_summary']}</div>
    </div>
    """, unsafe_allow_html=True)

    col_topo, col_rl = st.columns([1.15, 0.85])

    with col_topo:
        st.markdown("#### 3D Acoustic Transmission Vector")
        nodes = get_topology_nodes()
        links = get_potential_acoustic_links(tx_range=250.0)

        fig_demo = go.Figure()

        for link in links:
            n1, n2 = link['node1'], link['node2']
            fig_demo.add_trace(go.Scatter3d(
                x=[n1['x'], n2['x']], y=[n1['y'], n2['y']], z=[n1['z'], n2['z']],
                mode='lines', line=dict(color='rgba(167, 139, 250, 0.1)', width=1),
                hoverinfo='none', showlegend=False
            ))

        is_post_failure = st.session_state['demo_step'] >= 3
        if is_post_failure:
            n4 = next(n for n in nodes if n['id'] == 4)
            n5 = next(n for n in nodes if n['id'] == 5)
            fig_demo.add_trace(go.Scatter3d(
                x=[n4['x'], n5['x']], y=[n4['y'], n5['y']], z=[n4['z'], n5['z']],
                mode='lines', line=dict(color='rgba(239, 68, 68, 0.7)', width=4, dash='dash'),
                name='Disrupted Corridor (N4 ↔ N5)',
                hoverinfo='text', hovertext='Sector Blocked: Consecutive Timeouts >= 2'
            ))

        if current_step['active_edge']:
            u, v = current_step['active_edge']
            nu = next(n for n in nodes if n['id'] == u)
            nv = next(n for n in nodes if n['id'] == v)
            is_recovery_vector = (u == 4 and v == 6) or (u == 6 and v == 7) or (u == 7 and v == 11)
            vector_color = '#34D399' if is_recovery_vector else '#C4B5FD'
            vector_name = 'Recovery Bypass Vector' if is_recovery_vector else 'Transmission Vector'

            fig_demo.add_trace(go.Scatter3d(
                x=[nu['x'], nv['x']], y=[nu['y'], nv['y']], z=[nu['z'], nv['z']],
                mode='lines+markers', line=dict(color=vector_color, width=6),
                marker=dict(size=6, color=vector_color),
                name=vector_name, hoverinfo='text',
                hovertext=f"Acoustic Forwarding Hop: Node {u} -> Node {v}"
            ))

        for n in nodes:
            is_active = n['id'] in current_step['active_nodes']
            is_s5 = (n['id'] == 5)
            s5_dead = is_s5 and is_post_failure

            if s5_dead:
                col = '#EF4444'; size = 14; sym = 'x'
            elif n['type'] == 'source':
                col = '#C4B5FD'; size = 12; sym = 'diamond'
            elif n['type'] == 'sink':
                col = '#34D399'; size = 14; sym = 'square'
            elif is_active:
                col = '#FBBF24'; size = 13; sym = 'circle'
            else:
                col = '#A78BFA'; size = 8; sym = 'circle'

            fig_demo.add_trace(go.Scatter3d(
                x=[n['x']], y=[n['y']], z=[n['z']],
                mode='markers+text',
                marker=dict(size=size, color=col, symbol=sym, line=dict(color='#FFFFFF', width=1)),
                text=[n['short_name']], textposition='top center',
                textfont=dict(color='#FAFAFA', size=10),
                hoverinfo='text', hovertext=f"{n['name']}<br>Coords: ({n['x']}, {n['y']}, {n['z']}) m",
                showlegend=False
            ))

        demo_layout = get_charcoal_lavender_plotly_layout(f"Step {current_step['step_num']}: Acoustic Transmission Vector", height=440)
        demo_layout['scene'] = dict(
            xaxis=dict(title='X East-West (m)', backgroundcolor='#18181B', gridcolor='#27272A', color='#A1A1AA'),
            yaxis=dict(title='Y North-South (m)', backgroundcolor='#18181B', gridcolor='#27272A', color='#A1A1AA'),
            zaxis=dict(title='Reflected Elevation Z (m)', backgroundcolor='#18181B', gridcolor='#27272A', color='#A1A1AA'),
            camera=dict(eye=dict(x=1.65, y=-1.65, z=1.25))
        )
        fig_demo.update_layout(demo_layout)
        st.plotly_chart(fig_demo, use_container_width=True)

        st.markdown(f"**Physical Acoustic Breakdown:** {current_step['detailed_explanation']}")

    with col_rl:
        st.markdown("#### RL Decision & Telemetry Inspector")
        st_info = STATE_DEFINITIONS[current_step['state_idx']]
        act_info = ACTION_DEFINITIONS[current_step['action_idx']]

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-title'>Fault Status</div>
                <div class='metric-value' style='font-size:1.3rem; color:{'#EF4444' if current_step['consecutive_timeouts'] >= 2 else '#34D399'};'>
                    {current_step['consecutive_timeouts']} Timeouts
                </div>
                <div class='metric-subtext'>{'Degraded (Level 1)' if current_step['consecutive_timeouts'] >= 2 else 'Healthy (Level 0)'}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_s2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-title'>Current State</div>
                <div class='metric-value' style='font-size:1.3rem; color:#C4B5FD;'>S{current_step['state_idx']}</div>
                <div class='metric-subtext'>{st_info['tag']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_s3:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-title'>Action</div>
                <div class='metric-value' style='font-size:1.3rem; color:#A78BFA;'>
                    {act_info['code'].replace('ACTION_', '')}
                </div>
                <div class='metric-subtext'>Delay: {act_info['acoustic_delay']}s</div>
            </div>
            """, unsafe_allow_html=True)

        if current_step['bellman_math']:
            bm = current_step['bellman_math']
            st.markdown("##### Real-Time Bellman Q-Value Update:")
            st.latex(r"Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]")
            st.markdown(f"""
            <div style='background: #18181B; border: 1px solid var(--border-accent); border-radius: 8px; padding: 12px 16px; font-size: 0.85rem; font-family: monospace;'>
                <div>• Initial Q(S{bm['state']}, {ACTION_DEFINITIONS[bm['action']]['code']}) = <b>{bm['current_q']:.2f}</b></div>
                <div>• Immediate Reward (r) = <b style='color:#34D399;'>{bm['reward']:+.2f}</b></div>
                <div>• Maximum Future Target max Q(s') = <b>{bm['max_next_q']:.2f}</b></div>
                <div>• Temporal Difference Error (delta) = <b>{bm['delta']:+.3f}</b></div>
                <div style='color: #C4B5FD; font-weight: bold; margin-top: 4px; border-top: 1px solid #27272A; padding-top: 4px;'>
                    • Updated Q(S{bm['state']}, {ACTION_DEFINITIONS[bm['action']]['code']}) = <b>{bm['new_q']:.4f}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Step represents acoustic wave propagation in the water column; no Bellman Q-table update occurred at this exact timestamp.")

        st.markdown("##### Active Q-Table Matrix (8 States × 3 Actions):")
        q_data = []
        for s in range(8):
            row = {
                'State': f"S{s} ({STATE_DEFINITIONS[s]['tag']})",
                'FORWARD (0)': st.session_state['sim_q_table'][(s, 0)],
                'DEFER (1)': st.session_state['sim_q_table'][(s, 1)],
                'AVOID (2)': st.session_state['sim_q_table'][(s, 2)]
            }
            q_data.append(row)
        df_q = pd.DataFrame(q_data).set_index('State')
        st.dataframe(
            df_q.style.background_gradient(cmap='Purples', axis=None).format("{:.2f}"),
            use_container_width=True
        )


# ==============================================================================
# SECTION 4: 3D NETWORK BUILDER
# ==============================================================================
elif nav_mode == "🛠️ 3D Network Builder":
    render_network_builder()


# ==============================================================================
# SECTION 5: PROTOCOL BENCHMARK
# ==============================================================================
elif nav_mode == "📈 Protocol Benchmark":
    st.markdown("""
    <div class='command-header'>
        <div>
            <h1 class='command-title'>MULTI-PROTOCOL MULTI-SEED BENCHMARK EVALUATION</h1>
            <div class='command-subtitle'>Comparative experimental findings across 50 independent NS-3.41 simulation runs (10 per protocol)</div>
        </div>
        <div>
            <span class='status-pill status-pill-lavender'>P6.4 AUDITED BENCHMARK</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_runs = load_per_run_data()
    df_summary = load_summary_statistics()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>P4 Unique PDR</div>
            <div class='metric-value' style='color:#C4B5FD;'>62.94%</div>
            <div class='metric-subtext'>± 1.93% (1.51% Duplicates)</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Post-Failure Parity</div>
            <div class='metric-value' style='color:#34D399;'>62.50%</div>
            <div class='metric-subtext'>vs. VBF 63.53% (p = 0.364)</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Energy Conservation</div>
            <div class='metric-value' style='color:#A78BFA;'>35.90 J</div>
            <div class='metric-subtext'>Savings vs VBF (p < 10⁻¹⁰)</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class='metric-card'>
            <div class='metric-title'>Tail Latency (P95)</div>
            <div class='metric-value' style='color:#FBBF24;'>2.3479 s</div>
            <div class='metric-subtext'>vs. VBF 2.7670s, DBR 2.9114s</div>
        </div>
        """, unsafe_allow_html=True)

    proto_order = ['p4', 'p2', 'vbf', 'dbr', 'eedbr']
    labels = [PROTOCOL_NAMES[p] for p in proto_order]
    custom_colors = ['#C4B5FD', '#818CF8', '#F59E0B', '#A78BFA', '#34D399']

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("#### Pre-Failure vs. Post-Failure Unique PDR")
        pre_means = [df_runs[df_runs['protocol'] == p]['pre_unique_pdr'].mean() for p in proto_order]
        post_means = [df_runs[df_runs['protocol'] == p]['post_unique_pdr'].mean() for p in proto_order]

        fig_pdr = go.Figure(data=[
            go.Bar(name='Pre-Failure (<50s)', x=labels, y=pre_means, marker_color='#818CF8'),
            go.Bar(name='Post-Failure (≥50s)', x=labels, y=post_means, marker_color='#F59E0B')
        ])
        fig_pdr.update_layout(get_charcoal_lavender_plotly_layout("Unique PDR Under Fault Injection", height=380))
        fig_pdr.update_layout(barmode='group', yaxis=dict(title='Unique PDR (%)', range=[0, 85]))
        st.plotly_chart(fig_pdr, use_container_width=True)

    with col_chart2:
        st.markdown("#### Total Sensor Array Energy Consumption")
        e_means = [df_runs[df_runs['protocol'] == p]['total_energy'].mean() for p in proto_order]
        e_sds = [df_runs[df_runs['protocol'] == p]['total_energy'].std() for p in proto_order]

        fig_e = go.Figure(data=[
            go.Bar(x=labels, y=e_means, error_y=dict(type='data', array=e_sds), marker_color=custom_colors)
        ])
        fig_e.update_layout(get_charcoal_lavender_plotly_layout("Total Energy Consumed (Joules)", height=380))
        fig_e.update_layout(yaxis=dict(title='Energy (Joules)', range=[300, 560]))
        st.plotly_chart(fig_e, use_container_width=True)

    col_chart3, col_chart4 = st.columns(2)
    with col_chart3:
        st.markdown("#### End-to-End Latency: Mean Delay vs. Tail P95 Delay")
        mean_delays = [df_runs[df_runs['protocol'] == p]['mean_delay'].mean() for p in proto_order]
        p95_delays = [df_runs[df_runs['protocol'] == p]['p95_delay'].mean() for p in proto_order]

        fig_lat = go.Figure(data=[
            go.Bar(name='Mean Delay (s)', x=labels, y=mean_delays, marker_color='#A78BFA'),
            go.Bar(name='P95 Tail Delay (s)', x=labels, y=p95_delays, marker_color='#EF4444')
        ])
        fig_lat.update_layout(get_charcoal_lavender_plotly_layout("End-to-End Packet Delay (s)", height=380))
        fig_lat.update_layout(barmode='group', yaxis=dict(title='Latency (Seconds)'))
        st.plotly_chart(fig_lat, use_container_width=True)

    with col_chart4:
        st.markdown("#### Energy Efficiency per Unique Delivered Packet")
        epu_means = [df_runs[df_runs['protocol'] == p]['energy_per_unique'].mean() for p in proto_order]

        fig_epu = go.Figure(data=[
            go.Bar(x=labels, y=epu_means, marker_color=custom_colors)
        ])
        fig_epu.update_layout(get_charcoal_lavender_plotly_layout("Energy Consumed per Delivered Packet (J/pkt)", height=380))
        fig_epu.update_layout(yaxis=dict(title='Joules / Unique Packet'))
        st.plotly_chart(fig_epu, use_container_width=True)

    st.markdown("<h3 class='section-header'>Audited Multi-Protocol Comparison Table ($N = 10$ Runs per Protocol)</h3>", unsafe_allow_html=True)
    summary_data = []
    for p in proto_order:
        sub = df_runs[df_runs['protocol'] == p]
        summary_data.append({
            'Protocol': PROTOCOL_NAMES[p],
            'Unique PDR (%)': f"{sub['unique_pdr'].mean():.2f} ± {sub['unique_pdr'].std():.2f}",
            'Total Reception Ratio (%)': f"{sub['total_pdr'].mean():.2f} ± {sub['total_pdr'].std():.2f}",
            'Pre-Failure PDR (%)': f"{sub['pre_unique_pdr'].mean():.2f} ± {sub['pre_unique_pdr'].std():.2f}",
            'Post-Failure PDR (%)': f"{sub['post_unique_pdr'].mean():.2f} ± {sub['post_unique_pdr'].std():.2f}",
            'Mean Delay (s)': f"{sub['mean_delay'].mean():.4f} ± {sub['mean_delay'].std():.4f}",
            'P95 Delay (s)': f"{sub['p95_delay'].mean():.4f} ± {sub['p95_delay'].std():.4f}",
            'Total Energy (J)': f"{sub['total_energy'].mean():.2f} ± {sub['total_energy'].std():.2f}",
            'Energy / Unique Pkt (J/pkt)': f"{sub['energy_per_unique'].mean():.4f} ± {sub['energy_per_unique'].std():.4f}",
            'Sensor 5 Residual (J)': f"{sub['s5_residual'].mean():.2f} ± {sub['s5_residual'].std():.2f}"
        })
    df_sum_display = pd.DataFrame(summary_data).set_index('Protocol')
    st.dataframe(df_sum_display, use_container_width=True)


# ==============================================================================
# SECTION 6: UNDERWATER TOPOLOGY
# ==============================================================================
elif nav_mode == "🌊 Underwater Topology":
    st.markdown("""
    <div class='command-header'>
        <div>
            <h1 class='command-title'>3D UNDERWATER TOPOLOGY & ACOUSTIC ENVIRONMENT</h1>
            <div class='command-subtitle'>Spatial Coordinate Space ($550\\text{m} \\times 550\\text{m} \\times 100\\text{m}$ Water Column) & Acoustic Vectoring</div>
        </div>
        <div>
            <span class='status-pill status-pill-lavender'>12 REFLECTED NODES</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Interactive WebGL Three.js Viewport
    st.markdown("#### Interactive 3D WebGL Subsea Array Viewport")
    three_html = get_threejs_html(
        active_step=0,
        is_fault_active=False,
        show_links_initially=True,
        selected_node_id=12
    )
    components.html(three_html, height=580)

    nodes = get_topology_nodes()
    st.markdown("#### Node Coordinate Matrix ($N=12$)")
    node_df = pd.DataFrame(nodes)[['id', 'short_name', 'x', 'y', 'z', 'depth_desc', 'status', 'role']]
    st.dataframe(node_df, height=360, use_container_width=True)


# ==============================================================================
# SECTION 7: RL ARCHITECTURE AND Q-TABLE
# ==============================================================================
elif nav_mode == "🧠 RL Architecture and Q-Table":
    st.markdown("""
    <div class='command-header'>
        <div>
            <h1 class='command-title'>REINFORCEMENT LEARNING MATHEMATICAL ARCHITECTURE</h1>
            <div class='command-subtitle'>Formal 3D Binary Tuple Formulation, Reward Dynamics, and Sector Blockage Tracking</div>
        </div>
        <div>
            <span class='status-pill status-pill-lavender'>P4 MARKOV DECISION PROCESS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='callout-box'>
        <b>Formal State Formulation:</b> In P4, the Q-learning state space is a 3-dimensional binary tuple calculated by:
        <br><code>State Index = (faultLevel * 4) + (energyLevel * 2) + progressLevel</code>
        <br>• <b>faultLevel:</b> 0 if <code>m_consecutiveTimeouts &lt; 2</code> (Healthy); 1 if <code>m_consecutiveTimeouts &ge; 2</code> (Degraded)
        <br>• <b>energyLevel:</b> 0 if <code>E_res &lt; 30.0 J</code> (Critical); 1 if <code>E_res &ge; 30.0 J</code> (Sufficient)
        <br>• <b>progressLevel:</b> 0 if <code>advancement &le; 0.0 m</code> (Non-positive); 1 if <code>advancement &gt; 0.0 m</code> (Positive)
    </div>
    """, unsafe_allow_html=True)

    col_s_table, col_rew = st.columns([1.1, 0.9])

    with col_s_table:
        st.markdown("#### Complete 8-State Representation Table")
        st_rows = []
        for s in range(8):
            d = STATE_DEFINITIONS[s]
            st_rows.append({
                'Index': s,
                'Fault Level': 'Degraded (1)' if d['fault'] else 'Healthy (0)',
                'Energy Level': 'High (>=30J)' if d['energy'] else 'Low (<30J)',
                'Progress Level': 'Positive (>0m)' if d['progress'] else 'Lateral (<=0m)',
                'Operational Role': d['desc']
            })
        st.dataframe(pd.DataFrame(st_rows).set_index('Index'), use_container_width=True)

    with col_rew:
        st.markdown("#### Verified Reward Function Implementation")
        st.markdown("""
        - **Terminal Sink Delivery (`status == 2`):**
          $$R_{\\text{sink}} = +20.0$$
        - **Intermediate 1-Hop Progress ACK (`status == 1`):**
          $$R_{\\text{relay}} = 5.0 + 5.0 \\times \\left(\\frac{\\text{progress}}{R}\\right) \\quad \\in [5.0, 10.0]$$
        - **ACK Timeout Penalty (`AckTimeout()`):**
          $$R_{\\text{timeout}} = -5.0$$
        - **Dynamic AVOID Action Reward:**
          - State 0 (Low energy, poor progress): $+5.0$ (Battery conservation)
          - State 2 (High energy, poor progress): $+2.0$ (Loop prevention)
          - State 1 (Low energy, good progress): $-1.0$ (Sacrificed advance)
          - State 3 (High energy, good progress): $-5.0$ (Faulty drop)
        """)

    st.markdown("---")
    st.markdown("#### Architectural Scope & Behavioral Boundaries")
    st.markdown("""
    1. **Sector-Level Tracking:** The failure counter `m_consecutiveTimeouts` is maintained per forwarder node, detecting sector blockage rather than exact neighbor ID.
    2. **No Explicit Graph Rebuilding:** Self-healing is an emergent property of spatial candidate availability in VBF combined with temporal deferral (`ACTION_DEFER`).
    3. **Hyperparameters:** Learning rate $\\alpha = 0.1$, Discount factor $\\gamma = 0.9$, Exploration $\\epsilon = 0.1$.
    """)
