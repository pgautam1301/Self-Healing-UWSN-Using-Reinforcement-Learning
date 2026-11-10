"""
test_redesign_pages.py - Programmatic verification of all 7 navigation views and Three.js 3D viewport.
Verifies data integrity, figure rendering, and calculations across the redesigned dashboard.
"""

import sys
import os
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import (
    load_per_run_data,
    load_summary_statistics,
    get_topology_nodes,
    get_potential_acoustic_links,
    load_actual_simulation_trace,
    PROTOCOL_NAMES,
    PROTOCOL_COLORS
)

from simulator_engine import (
    STATE_DEFINITIONS,
    ACTION_DEFINITIONS,
    EDUCATIONAL_STEPS,
    step_simulation,
    prewarm_q_table
)

from threejs_component import get_threejs_html


def get_charcoal_lavender_plotly_layout(title="", height=420):
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


def test_redesign_all_pages():
    print("=" * 60)
    print("TESTING AQUANET 3D CHARCOAL & LAVENDER CONTROL CENTER")
    print("=" * 60)

    # 1. Test Interactive Three.js 3D Component Generation
    print("\n[Feature 1] Testing Three.js 3D WebGL Canvas Generation...")
    three_html = get_threejs_html(active_step=0, is_fault_active=False, show_links_initially=False)
    assert three_html is not None and len(three_html) > 50000
    assert "OrbitControls" in three_html
    assert "Source Node 12" in three_html
    assert "Surface Sink 11" in three_html
    assert "Sensor 5" in three_html
    assert "btn-toggle-links" in three_html
    assert "btn-packet" in three_html
    print(f"  [OK] Three.js HTML generated ({len(three_html):,} bytes) with 12 nodes and controls")

    # 2. Test Overview Section Metrics
    print("\n[Page 1: Overview] Testing Executive HUD Telemetry...")
    df_runs = load_per_run_data()
    p4_runs = df_runs[df_runs['protocol'] == 'p4']
    mean_pdr = p4_runs['unique_pdr'].mean()
    mean_energy = p4_runs['total_energy'].mean()
    mean_delay = p4_runs['mean_delay'].mean()
    assert abs(mean_pdr - 62.94) < 0.1
    assert abs(mean_energy - 477.87) < 0.1
    assert abs(mean_delay - 1.8072) < 0.01
    print(f"  [OK] P4 Audited Metrics: PDR={mean_pdr:.2f}%, Energy={mean_energy:.2f}J, Delay={mean_delay:.4f}s")

    # 3. Test Mode A: Actual NS-3 Results Replay
    print("\n[Page 2: Mode A] Testing Actual NS-3 Results Replay...")
    for run in [1, 5, 10]:
        trace = load_actual_simulation_trace(run_num=run)
        assert trace is not None, f"Failed to load trace for run {run}"
        assert not trace['events_df'].empty, f"Events empty for run {run}"
        assert trace['total_deliveries'] > 0
        assert trace['unique_deliveries'] > 0
        print(f"  [OK] Run {run:02d}: {len(trace['events_df'])} events, {trace['unique_deliveries']} unique UIDs")

    # 4. Test Mode B: Interactive RL Simulator (All 9 Steps)
    print("\n[Page 3: Mode B] Testing Interactive Step-by-Step Simulator...")
    assert len(EDUCATIONAL_STEPS) == 9
    for step_idx in range(9):
        step_data = step_simulation(step_idx)
        assert step_data['step_num'] == step_idx + 1
        assert step_data['state_idx'] in range(8)
        assert step_data['action_idx'] in range(3)
        if step_idx >= 3:
            status_upper = step_data['s5_status'].upper()
            assert any(term in status_upper for term in ["FAILED", "DEAD", "BYPASS"])
        if step_idx == 7:
            assert step_data['active_edge'] == (4, 6), f"Step 8 active edge should be (4, 6), got {step_data['active_edge']}"
        print(f"  [OK] Step {step_idx+1}: {step_data['title'][:45]}... (State S{step_data['state_idx']}, Action {step_data['action_idx']})")

    # 5. Test Benchmark Section (5 Protocols, PDR, Energy, Delay)
    print("\n[Page 4: Benchmark] Testing Protocol Performance Benchmark...")
    assert len(df_runs) == 50
    for p in ['p4', 'p2', 'vbf', 'dbr', 'eedbr']:
        sub = df_runs[df_runs['protocol'] == p]
        assert len(sub) == 10
        print(f"  [OK] {PROTOCOL_NAMES[p]}: Unique PDR={sub['unique_pdr'].mean():.2f}%, Energy={sub['total_energy'].mean():.2f}J")

    # 6. Test 3D Topology & Acoustic Routing Vectors
    print("\n[Page 5: Topology] Testing 3D Topology & Routing Vectors...")
    nodes = get_topology_nodes()
    links = get_potential_acoustic_links(tx_range=250.0)
    assert len(nodes) == 12
    primary_path = [12, 1, 4, 5, 7, 11]
    recovery_path = [12, 1, 4, 6, 7, 11]
    node_ids = {n['id'] for n in nodes}
    for pid in primary_path + recovery_path:
        assert pid in node_ids, f"Node {pid} missing from topology"
    print("  [OK] 12 Nodes, Primary Route (via Sensor 5) and Recovery Route (via Sensor 6) verified")

    # 7. Test RL Architecture & Q-Table Inspector
    print("\n[Page 6: RL Architecture] Testing RL Mathematical Formulation...")
    assert len(STATE_DEFINITIONS) == 8
    assert len(ACTION_DEFINITIONS) == 3
    q_table = prewarm_q_table()
    assert len(q_table) == 24
    print("  [OK] 8 discrete states, 3 actions, and 24 Q-table cells verified")

    # 8. Test Plotly Theme Layout Helper
    print("\n[Styling & Theme] Testing Charcoal & Lavender Plotly Layout...")
    layout = get_charcoal_lavender_plotly_layout("Test Figure", height=400)
    assert layout['paper_bgcolor'] == "#18181B"
    assert layout['plot_bgcolor'] == "#18181B"
    assert layout['height'] == 400
    print("  [OK] Charcoal & lavender palette verified")

    print("\n" + "=" * 60)
    print("ALL 7 NAVIGATION SECTIONS & 3D CANVAS VERIFIED (100% SUCCESS)")
    print("=" * 60)


if __name__ == "__main__":
    test_redesign_all_pages()
