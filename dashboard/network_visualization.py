"""
network_visualization.py - Plotly Visual Canvas for AquaNet 3D Underwater Network Builder.
Implements 3D and 2D interactive topological visualizations with 60-30-10 palette.
- 60% Primary Canvas: Deep Ocean Navy (#0B1928)
- 30% Structural Secondary: Ocean Teal (#174B50)
- 10% Visual Accent: Luminous Aqua (#45D6CB)
Semantic Colors:
- Source: #45D6CB (Luminous Aqua)
- Sink: #10B981 (Emerald Green)
- Active Sensor: #38BDF8 (Sky Ocean)
- Failed Sensor: #EF4444 (Crimson Red)
- Selection Highlight: #F59E0B (Amber Gold)
"""

import math
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import plotly.graph_objects as go
from network_models import NetworkTopology, Node


# Charcoal & Lavender Color Tokens
COLOR_PRIMARY_BG = "#09090B"      # Pure Black / Charcoal Background
COLOR_SECONDARY_GRID = "#27272A"  # Dark Panel Grid Line
COLOR_SECONDARY_BORDER = "#3F3F46"
COLOR_ACCENT = "#C4B5FD"          # Lavender Accent
COLOR_TEXT_MAIN = "#FAFAFA"
COLOR_TEXT_MUTED = "#A1A1AA"

# Semantic Node Colors
COLOR_NODE_SOURCE = "#C4B5FD"     # Lavender
COLOR_NODE_SINK = "#34D399"       # Emerald Green
COLOR_NODE_SENSOR = "#A78BFA"     # Purple
COLOR_NODE_FAILED = "#EF4444"     # Crimson Alert
COLOR_NODE_SELECTED = "#FBBF24"   # Golden Highlight
COLOR_LINK_VALID = "rgba(167, 139, 250, 0.45)"    # Translucent Lavender / Purple
COLOR_LINK_OVERRANGE = "rgba(239, 68, 68, 0.45)" # Translucent Red


def _create_circle_points_3d(center: Tuple[float, float, float], radius: float, plane: str = 'xy', steps: int = 40):
    """Generate 3D coordinates for a circle ring in a specific plane."""
    cx, cy, cz = center
    theta = np.linspace(0, 2 * np.pi, steps)
    if plane == 'xy':
        x = cx + radius * np.cos(theta)
        y = cy + radius * np.sin(theta)
        z = np.full_like(theta, cz)
    elif plane == 'xz':
        x = cx + radius * np.cos(theta)
        y = np.full_like(theta, cy)
        z = cz + radius * np.sin(theta)
    else:  # 'yz'
        x = np.full_like(theta, cx)
        y = cy + radius * np.cos(theta)
        z = cz + radius * np.sin(theta)
    return x.tolist(), y.tolist(), z.tolist()


def render_network_3d(
    topology: NetworkTopology,
    selected_node_id: Optional[int] = None,
    show_range_for_selected: bool = True,
    show_labels: bool = True,
    height: int = 580
) -> go.Figure:
    """
    Renders an interactive 3D WebGL visualization of the underwater sensor network.
    
    Includes:
    - Acoustic transmission links (color-coded by reachability)
    - Source, Sensor, Sink, and Failed nodes with distinct 3D glyphs
    - Selection ring and 3D acoustic transmission range sphere/rings
    - Seafloor / Surface reference framing
    """
    fig = go.Figure()

    if not topology.nodes:
        fig.add_annotation(
            text="No nodes in topology. Add nodes using the editor panel.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLOR_TEXT_MUTED)
        )
        fig.update_layout(
            paper_bgcolor=COLOR_PRIMARY_BG,
            plot_bgcolor=COLOR_PRIMARY_BG,
            height=height
        )
        return fig

    # 1. Links: Separate reachable vs overrange
    valid_link_x, valid_link_y, valid_link_z = [], [], []
    over_link_x, over_link_y, over_link_z = [], [], []
    link_mid_x, link_mid_y, link_mid_z, link_mid_texts = [], [], [], []

    for u, v in topology.links:
        if u not in topology.nodes or v not in topology.nodes:
            continue
        n1 = topology.nodes[u]
        n2 = topology.nodes[v]

        dist = n1.distance_to(n2)
        max_reach = min(n1.tx_range, n2.tx_range)
        is_reachable = dist <= max_reach

        if is_reachable:
            valid_link_x.extend([n1.x, n2.x, None])
            valid_link_y.extend([n1.y, n2.y, None])
            valid_link_z.extend([n1.z, n2.z, None])
        else:
            over_link_x.extend([n1.x, n2.x, None])
            over_link_y.extend([n1.y, n2.y, None])
            over_link_z.extend([n1.z, n2.z, None])

        # Midpoint for hover info
        link_mid_x.append((n1.x + n2.x) / 2.0)
        link_mid_y.append((n1.y + n2.y) / 2.0)
        link_mid_z.append((n1.z + n2.z) / 2.0)
        status_lbl = "REACHABLE" if is_reachable else "OUT OF RANGE"
        link_mid_texts.append(
            f"Link: Node {n1.id} ↔ Node {n2.id}<br>"
            f"Euclidean Dist: {dist:.1f} m<br>"
            f"Range Threshold: {max_reach:.1f} m<br>"
            f"Status: {status_lbl}"
        )

    # Add reachable links trace
    if valid_link_x:
        fig.add_trace(go.Scatter3d(
            x=valid_link_x, y=valid_link_y, z=valid_link_z,
            mode='lines',
            line=dict(color=COLOR_LINK_VALID, width=3),
            hoverinfo='none',
            name='Reachable Acoustic Link',
            showlegend=True
        ))

    # Add overrange links trace
    if over_link_x:
        fig.add_trace(go.Scatter3d(
            x=over_link_x, y=over_link_y, z=over_link_z,
            mode='lines',
            line=dict(color=COLOR_LINK_OVERRANGE, width=2, dash='dash'),
            hoverinfo='none',
            name='Out-of-Range Link',
            showlegend=True
        ))

    # Add link midpoint hover
    if link_mid_x:
        fig.add_trace(go.Scatter3d(
            x=link_mid_x, y=link_mid_y, z=link_mid_z,
            mode='markers',
            marker=dict(size=3, color='rgba(255,255,255,0.05)', opacity=0.1),
            hovertext=link_mid_texts,
            hoverinfo='text',
            name='Link Details',
            showlegend=False
        ))

    # 2. Nodes by Category
    node_list = list(topology.nodes.values())
    categories = [
        ('Source', [n for n in node_list if n.type == 'source'], COLOR_NODE_SOURCE, 'diamond', 12),
        ('Sink', [n for n in node_list if n.type == 'sink'], COLOR_NODE_SINK, 'square', 13),
        ('Sensor (Operational)', [n for n in node_list if n.type == 'sensor' and n.status != 'Failed'], COLOR_NODE_SENSOR, 'circle', 10),
        ('Failed Sensor', [n for n in node_list if n.status == 'Failed' or n.type in ('sensor_failed', 'failed')], COLOR_NODE_FAILED, 'cross', 12)
    ]

    for cat_name, nodes_in_cat, color, symbol, size in categories:
        if not nodes_in_cat:
            continue
        xs = [n.x for n in nodes_in_cat]
        ys = [n.y for n in nodes_in_cat]
        zs = [n.z for n in nodes_in_cat]
        texts = [f"N{n.id}" for n in nodes_in_cat] if show_labels else None
        hover_texts = [
            f"<b>Node {n.id}</b> ({n.name})<br>"
            f"Type: {n.type.upper()}<br>"
            f"Status: {n.status.upper()}<br>"
            f"Coordinates: ({n.x:.1f}, {n.y:.1f}, {n.z:.1f}) m<br>"
            f"Reflected Elevation: {n.z:.1f} m<br>"
            f"Tx Range: {n.tx_range:.1f} m<br>"
            f"Energy: {n.initial_energy:.1f} J"
            for n in nodes_in_cat
        ]

        mode = 'markers+text' if show_labels else 'markers'
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode=mode,
            text=texts,
            textposition='top center',
            textfont=dict(color=COLOR_TEXT_MAIN, size=10, family='Segoe UI'),
            marker=dict(
                size=size,
                color=color,
                symbol=symbol,
                line=dict(color="#FFFFFF", width=1),
                opacity=0.95
            ),
            hovertext=hover_texts,
            hoverinfo='text',
            name=cat_name,
            showlegend=True
        ))

    # 3. Selected Node Highlight & Range Rings
    if selected_node_id is not None and selected_node_id in topology.nodes:
        sel_node = topology.nodes[selected_node_id]
        fig.add_trace(go.Scatter3d(
            x=[sel_node.x], y=[sel_node.y], z=[sel_node.z],
            mode='markers',
            marker=dict(
                size=18,
                color='rgba(0,0,0,0)',
                line=dict(color=COLOR_NODE_SELECTED, width=4),
                symbol='circle'
            ),
            name=f'Selected (Node {sel_node.id})',
            hoverinfo='none',
            showlegend=True
        ))

        # Transmission Range Circles (XY, XZ, YZ rings)
        if show_range_for_selected and sel_node.tx_range > 0:
            R = sel_node.tx_range
            center = (sel_node.x, sel_node.y, sel_node.z)

            for plane, col in [('xy', 'rgba(69, 214, 203, 0.4)'),
                              ('xz', 'rgba(23, 75, 80, 0.5)'),
                              ('yz', 'rgba(56, 189, 248, 0.35)')]:
                rx, ry, rz = _create_circle_points_3d(center, R, plane=plane, steps=50)
                fig.add_trace(go.Scatter3d(
                    x=rx, y=ry, z=rz,
                    mode='lines',
                    line=dict(color=col, width=2, dash='dot'),
                    hoverinfo='none',
                    name=f'Tx Range ({R:.0f}m - {plane.upper()})',
                    showlegend=False
                ))

    # Bounding Box Framing
    bounds = topology.get_bounding_box()
    span_x = max(bounds['max_x'] - bounds['min_x'], 100.0)
    span_y = max(bounds['max_y'] - bounds['min_y'], 100.0)
    span_z = max(bounds['max_z'] - bounds['min_z'], 50.0)
    pad_x = span_x * 0.15
    pad_y = span_y * 0.15
    pad_z = span_z * 0.2

    fig.update_layout(
        paper_bgcolor=COLOR_PRIMARY_BG,
        plot_bgcolor=COLOR_PRIMARY_BG,
        font=dict(color=COLOR_TEXT_MAIN, family="Segoe UI, sans-serif"),
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            bgcolor="rgba(11, 25, 40, 0.85)",
            bordercolor=COLOR_SECONDARY_GRID,
            borderwidth=1,
            font=dict(color=COLOR_TEXT_MAIN, size=11),
            x=0.01, y=0.99
        ),
        scene=dict(
            bgcolor=COLOR_PRIMARY_BG,
            xaxis=dict(
                title=dict(text='X East-West (m)', font=dict(color=COLOR_ACCENT, size=11)),
                backgroundcolor=COLOR_PRIMARY_BG,
                gridcolor=COLOR_SECONDARY_GRID,
                linecolor=COLOR_SECONDARY_BORDER,
                tickfont=dict(color=COLOR_TEXT_MUTED, size=9),
                range=[bounds['min_x'] - pad_x, bounds['max_x'] + pad_x]
            ),
            yaxis=dict(
                title=dict(text='Y North-South (m)', font=dict(color=COLOR_ACCENT, size=11)),
                backgroundcolor=COLOR_PRIMARY_BG,
                gridcolor=COLOR_SECONDARY_GRID,
                linecolor=COLOR_SECONDARY_BORDER,
                tickfont=dict(color=COLOR_TEXT_MUTED, size=9),
                range=[bounds['min_y'] - pad_y, bounds['max_y'] + pad_y]
            ),
            zaxis=dict(
                title=dict(text='Reflected Elevation Z (m)', font=dict(color=COLOR_ACCENT, size=11)),
                backgroundcolor=COLOR_PRIMARY_BG,
                gridcolor=COLOR_SECONDARY_GRID,
                linecolor=COLOR_SECONDARY_BORDER,
                tickfont=dict(color=COLOR_TEXT_MUTED, size=9),
                range=[max(0.0, bounds['min_z'] - pad_z), bounds['max_z'] + pad_z]
            ),
            camera=dict(
                eye=dict(x=1.7, y=-1.7, z=1.3),
                up=dict(x=0, y=0, z=1)
            )
        )
    )

    return fig


def render_network_2d(
    topology: NetworkTopology,
    plane: str = 'xz',
    selected_node_id: Optional[int] = None,
    show_range: bool = True,
    height: int = 420
) -> go.Figure:
    """
    Renders an orthogonal 2D projection of the underwater network.
    - 'xz': Depth Profile (X East-West vs Reflected Elevation Z)
    - 'xy': Top-Down Surface View (X East-West vs Y North-South)
    - 'yz': Cross-Section Profile (Y North-South vs Reflected Elevation Z)
    """
    fig = go.Figure()

    if not topology.nodes:
        fig.add_annotation(
            text="No nodes to display in 2D projection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color=COLOR_TEXT_MUTED)
        )
        fig.update_layout(paper_bgcolor=COLOR_PRIMARY_BG, plot_bgcolor=COLOR_PRIMARY_BG, height=height)
        return fig

    axis_map = {
        'xz': ('x', 'z', 'X East-West (m)', 'Reflected Elevation Z (m)'),
        'xy': ('x', 'y', 'X East-West (m)', 'Y North-South (m)'),
        'yz': ('y', 'z', 'Y North-South (m)', 'Reflected Elevation Z (m)')
    }
    h_attr, v_attr, h_title, v_title = axis_map.get(plane, axis_map['xz'])

    # 1. Links
    for u, v in topology.links:
        if u not in topology.nodes or v not in topology.nodes:
            continue
        n1 = topology.nodes[u]
        n2 = topology.nodes[v]
        dist = n1.distance_to(n2)
        max_reach = min(n1.tx_range, n2.tx_range)
        is_reach = dist <= max_reach
        color = COLOR_LINK_VALID if is_reach else COLOR_LINK_OVERRANGE
        dash = 'solid' if is_reach else 'dash'

        fig.add_trace(go.Scatter(
            x=[getattr(n1, h_attr), getattr(n2, h_attr)],
            y=[getattr(n1, v_attr), getattr(n2, v_attr)],
            mode='lines',
            line=dict(color=color, width=1.5, dash=dash),
            hoverinfo='text',
            hovertext=f"Link {n1.id} ↔ {n2.id} ({dist:.1f}m)",
            showlegend=False
        ))

    # 2. Selected Range Circle in 2D
    if selected_node_id is not None and show_range and selected_node_id in topology.nodes:
        sel_node = topology.nodes[selected_node_id]
        if sel_node.tx_range > 0:
            R = sel_node.tx_range
            c_h = getattr(sel_node, h_attr)
            c_v = getattr(sel_node, v_attr)
            theta = np.linspace(0, 2 * np.pi, 60)
            circle_h = c_h + R * np.cos(theta)
            circle_v = c_v + R * np.sin(theta)

            fig.add_trace(go.Scatter(
                x=circle_h, y=circle_v,
                mode='lines',
                line=dict(color=COLOR_ACCENT, width=1.5, dash='dot'),
                fill='toself',
                fillcolor='rgba(69, 214, 203, 0.08)',
                name=f'Tx Reach ({R:.0f}m)',
                hoverinfo='none',
                showlegend=True
            ))

    # 3. Nodes
    node_list = list(topology.nodes.values())
    categories = [
        ('Source', [n for n in node_list if n.type == 'source'], COLOR_NODE_SOURCE, 'diamond', 14),
        ('Sink', [n for n in node_list if n.type == 'sink'], COLOR_NODE_SINK, 'square', 14),
        ('Sensor', [n for n in node_list if n.type == 'sensor' and n.status != 'Failed'], COLOR_NODE_SENSOR, 'circle', 11),
        ('Failed', [n for n in node_list if n.status == 'Failed' or n.type in ('sensor_failed', 'failed')], COLOR_NODE_FAILED, 'x', 14)
    ]

    for cat_name, nodes_in_cat, color, symbol, size in categories:
        if not nodes_in_cat:
            continue
        hs = [getattr(n, h_attr) for n in nodes_in_cat]
        vs = [getattr(n, v_attr) for n in nodes_in_cat]
        labels = [f"N{n.id}" for n in nodes_in_cat]
        hover_texts = [
            f"<b>Node {n.id}</b> ({n.name})<br>"
            f"Type: {n.type.upper()}<br>"
            f"Status: {n.status.upper()}<br>"
            f"Coords: ({n.x:.1f}, {n.y:.1f}, {n.z:.1f}) m<br>"
            f"Energy: {n.initial_energy:.1f} J<br>"
            f"Range: {n.tx_range:.1f} m"
            for n in nodes_in_cat
        ]

        fig.add_trace(go.Scatter(
            x=hs, y=vs,
            mode='markers+text',
            text=labels,
            textposition='top center',
            textfont=dict(color=COLOR_TEXT_MAIN, size=10),
            marker=dict(size=size, color=color, symbol=symbol, line=dict(color='#FFFFFF', width=1)),
            hovertext=hover_texts,
            hoverinfo='text',
            name=cat_name
        ))

    # 4. Selection Highlight
    if selected_node_id is not None and selected_node_id in topology.nodes:
        sel_node = topology.nodes[selected_node_id]
        fig.add_trace(go.Scatter(
            x=[getattr(sel_node, h_attr)],
            y=[getattr(sel_node, v_attr)],
            mode='markers',
            marker=dict(
                size=22,
                color='rgba(0,0,0,0)',
                line=dict(color=COLOR_NODE_SELECTED, width=3),
                symbol='circle'
            ),
            name='Selected Node',
            hoverinfo='none',
            showlegend=False
        ))

    fig.update_layout(
        title=dict(text=f"2D Orthogonal Projection ({plane.upper()})", font=dict(color=COLOR_TEXT_MAIN, size=13)),
        paper_bgcolor=COLOR_PRIMARY_BG,
        plot_bgcolor=COLOR_PRIMARY_BG,
        font=dict(color=COLOR_TEXT_MAIN, family="Segoe UI, sans-serif"),
        height=height,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(
            title=dict(text=h_title, font=dict(color=COLOR_ACCENT, size=11)),
            gridcolor=COLOR_SECONDARY_GRID,
            linecolor=COLOR_SECONDARY_BORDER,
            tickfont=dict(color=COLOR_TEXT_MUTED, size=9)
        ),
        yaxis=dict(
            title=dict(text=v_title, font=dict(color=COLOR_ACCENT, size=11)),
            gridcolor=COLOR_SECONDARY_GRID,
            linecolor=COLOR_SECONDARY_BORDER,
            tickfont=dict(color=COLOR_TEXT_MUTED, size=9)
        ),
        legend=dict(
            bgcolor="rgba(11, 25, 40, 0.85)",
            bordercolor=COLOR_SECONDARY_GRID,
            borderwidth=1,
            font=dict(color=COLOR_TEXT_MAIN, size=10)
        )
    )

    return fig
