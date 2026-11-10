"""
network_builder.py - AquaNet 3D Visual Underwater Network Builder UI.
Implements the interactive builder workspace, node/link manipulation, configuration management,
and topology verification adhering strictly to the 60-30-10 color guidelines.
"""

import json
from typing import Optional
import streamlit as st
import pandas as pd

from network_models import NetworkTopology, Node, get_default_project_topology
from config_manager import ConfigManager
from network_visualization import render_network_3d, render_network_2d


def init_builder_session():
    """Initializes session state objects for the network builder."""
    if "current_topology" not in st.session_state:
        st.session_state.current_topology = get_default_project_topology()
    if "selected_node_id" not in st.session_state:
        # Default selection to Node 5 (failed node) or first available node
        st.session_state.selected_node_id = 5 if 5 in st.session_state.current_topology.nodes else 1
    if "builder_view_mode" not in st.session_state:
        st.session_state.builder_view_mode = "3D Interactive Volume"
    if "config_manager" not in st.session_state:
        st.session_state.config_manager = ConfigManager()


def render_network_builder():
    """Main entry point for the AquaNet 3D Network Builder view."""
    init_builder_session()
    topo: NetworkTopology = st.session_state.current_topology
    cfg_mgr: ConfigManager = st.session_state.config_manager

    # Header section
    st.markdown("<h2 class='section-header' style='margin-bottom: 4px;'>AquaNet 3D Underwater Network Builder</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #A1A1AA; font-size: 0.9rem; margin-bottom: 16px;'>Interactive visual workspace for custom UWSN deployment, acoustic link reachability verification, and JSON configuration management.</p>", unsafe_allow_html=True)

    # Topology Summary Metrics Bar
    bounds = topo.get_bounding_box()
    vol_x = max(bounds['max_x'] - bounds['min_x'], 1.0)
    vol_y = max(bounds['max_y'] - bounds['min_y'], 1.0)
    vol_z = max(bounds['max_z'] - bounds['min_z'], 1.0)
    bounding_volume_m3 = (vol_x * vol_y * vol_z) / 1e6  # in 10^6 m^3

    is_valid, validation_issues = topo.validate()
    src_node = topo.get_source_node()
    sink_node = topo.get_sink_node()
    num_nodes = len(topo.nodes)
    num_links = len(topo.links)
    avg_degree = (2.0 * num_links / num_nodes) if num_nodes > 0 else 0.0

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-title'>Total Nodes</div>
            <div class='metric-value'>{num_nodes}</div>
            <div class='metric-subtext'>Sensors & Anchors</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        src_txt = f"Node {src_node.id}" if src_node else "None"
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-title'>Source Node</div>
            <div class='metric-value' style='font-size: 1.3rem; color: #C4B5FD;'>{src_txt}</div>
            <div class='metric-subtext'>Data Origin</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m3:
        sink_txt = f"Node {sink_node.id}" if sink_node else "None"
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-title'>Surface Sink</div>
            <div class='metric-value' style='font-size: 1.3rem; color: #34D399;'>{sink_txt}</div>
            <div class='metric-subtext'>Data Destination</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-title'>Acoustic Links</div>
            <div class='metric-value'>{num_links}</div>
            <div class='metric-subtext'>Avg Degree: {avg_degree:.1f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m5:
        status_color = "#34D399" if is_valid else "#EF4444"
        status_text = "READY / VALID" if is_valid else "ISSUES DETECTED"
        st.markdown(f"""
        <div class='metric-card' style='border-color: {status_color};'>
            <div class='metric-title'>Topology Health</div>
            <div class='metric-value' style='font-size: 1.15rem; color: {status_color};'>{status_text}</div>
            <div class='metric-subtext'>Span: {bounding_volume_m3:.2f}M m³</div>
        </div>
        """, unsafe_allow_html=True)

    # Validation Warning Box if issues present
    if not is_valid or validation_issues:
        alert_cls = "callout-box" if is_valid else "callout-box-alert"
        hdr_txt = "<b>Topology Validation Notes:</b>" if is_valid else "<b>Validation Warnings (Required Corrections):</b>"
        items_html = "".join([f"<li>{issue}</li>" for issue in validation_issues])
        st.markdown(f"""
        <div class='{alert_cls}'>
            {hdr_txt}
            <ul style='margin-bottom: 0; padding-left: 20px;'>{items_html}</ul>
        </div>
        """, unsafe_allow_html=True)

    # Main Canvas + Controls Split Layout
    col_canvas, col_tools = st.columns([1.6, 1.0])

    # -------------------------------------------------------------
    # LEFT COLUMN: INTERACTIVE VISUAL CANVAS
    # -------------------------------------------------------------
    with col_canvas:
        sub_c1, sub_c2, sub_c3 = st.columns([1.4, 0.8, 0.8])
        with sub_c1:
            view_mode = st.radio(
                "Projection:",
                ["3D Volume", "2D Depth Profile (X-Z)", "2D Surface (X-Y)"],
                horizontal=True,
                key="canvas_view_mode"
            )
        with sub_c2:
            show_range = st.checkbox("Show Tx Range", value=True, key="canvas_show_range")
        with sub_c3:
            show_labels = st.checkbox("Show Labels", value=True, key="canvas_show_labels")

        sel_id = st.session_state.selected_node_id

        if view_mode == "3D Volume":
            fig = render_network_3d(
                topo,
                selected_node_id=sel_id,
                show_range_for_selected=show_range,
                show_labels=show_labels,
                height=560
            )
            st.plotly_chart(fig, use_container_width=True)
        elif view_mode == "2D Depth Profile (X-Z)":
            fig = render_network_2d(
                topo,
                plane='xz',
                selected_node_id=sel_id,
                show_range=show_range,
                height=560
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = render_network_2d(
                topo,
                plane='xy',
                selected_node_id=sel_id,
                show_range=show_range,
                height=560
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tabbed Inspection Tables
        tab_nodes_tbl, tab_links_tbl = st.tabs(["Nodes Table", "Acoustic Links Table"])
        with tab_nodes_tbl:
            if topo.nodes:
                node_data = []
                for n in sorted(topo.nodes.values(), key=lambda x: x.id):
                    node_data.append({
                        "ID": n.id,
                        "Name": n.name,
                        "Type": n.type.upper(),
                        "X (m)": n.x,
                        "Y (m)": n.y,
                        "Elevation Z (m)": n.z,
                        "Range (m)": n.tx_range,
                        "Energy (J)": n.initial_energy,
                        "Status": n.status
                    })
                st.dataframe(pd.DataFrame(node_data), height=220, use_container_width=True)
            else:
                st.info("No nodes in current topology.")

        with tab_links_tbl:
            link_details = topo.get_link_details()
            if link_details:
                link_df_data = []
                for ld in link_details:
                    link_df_data.append({
                        "Link": f"Node {ld['u']} ↔ Node {ld['v']}",
                        "Distance (m)": ld["distance"],
                        "Max Reach (m)": ld["max_range"],
                        "Reachable": "YES" if ld["is_within_range"] else "NO (Overrange)",
                        "Impacted by Failure": "YES" if ld["involves_failed"] else "NO"
                    })
                st.dataframe(pd.DataFrame(link_df_data), height=220, use_container_width=True)
            else:
                st.info("No acoustic links configured. Use 'Auto-Connect Reachable' or add links manually.")

    # -------------------------------------------------------------
    # RIGHT COLUMN: BUILDER CONTROL PANELS
    # -------------------------------------------------------------
    with col_tools:
        builder_tab1, builder_tab2, builder_tab3, builder_tab4 = st.tabs([
            "Edit Node",
            "Add Node",
            "Links",
            "Templates & Files"
        ])

        # ---------------------------------------------------------
        # TAB 1: EDIT SELECTED NODE
        # ---------------------------------------------------------
        with builder_tab1:
            st.markdown("#### Selected Node Inspector")
            if topo.nodes:
                node_ids = sorted(list(topo.nodes.keys()))
                # Ensure selected_node_id exists
                if st.session_state.selected_node_id not in topo.nodes:
                    st.session_state.selected_node_id = node_ids[0]

                idx = node_ids.index(st.session_state.selected_node_id)
                picked_id = st.selectbox(
                    "Select Node to Inspect / Edit:",
                    node_ids,
                    index=idx,
                    format_func=lambda nid: f"Node {nid} ({topo.nodes[nid].name} - {topo.nodes[nid].type.upper()})"
                )
                st.session_state.selected_node_id = picked_id
                target_node = topo.nodes[picked_id]

                with st.form("edit_node_form"):
                    e_name = st.text_input("Name:", value=target_node.name)
                    e_type = st.selectbox(
                        "Node Type:",
                        ["sensor", "source", "sink", "sensor_failed"],
                        index=["sensor", "source", "sink", "sensor_failed"].index(
                            target_node.type if target_node.type in ["sensor", "source", "sink", "sensor_failed"] else "sensor"
                        )
                    )
                    c_x, c_y = st.columns(2)
                    with c_x:
                        e_x = st.number_input("X East-West (m):", value=float(target_node.x), step=10.0)
                    with c_y:
                        e_y = st.number_input("Y North-South (m):", value=float(target_node.y), step=10.0)

                    c_z, c_range = st.columns(2)
                    with c_z:
                        e_z = st.number_input("Elevation Z (m):", value=float(target_node.z), step=5.0)
                    with c_range:
                        e_range = st.number_input("Tx Range (m):", value=float(target_node.tx_range), step=25.0)

                    c_en, c_st = st.columns(2)
                    with c_en:
                        e_energy = st.number_input("Energy (J):", value=float(target_node.initial_energy), step=10.0)
                    with c_st:
                        e_status = st.selectbox(
                            "Status:",
                            ["Operational", "Failed", "Degraded"],
                            index=["Operational", "Failed", "Degraded"].index(
                                target_node.status if target_node.status in ["Operational", "Failed", "Degraded"] else "Operational"
                            )
                        )

                    e_notes = st.text_input("Notes:", value=target_node.notes)

                    submit_edit = st.form_submit_button("Save Node Changes", use_container_width=True)
                    if submit_edit:
                        target_node.name = e_name
                        target_node.type = e_type
                        target_node.x = float(e_x)
                        target_node.y = float(e_y)
                        target_node.z = float(e_z)
                        target_node.tx_range = float(e_range)
                        target_node.initial_energy = float(e_energy)
                        target_node.status = e_status
                        target_node.notes = e_notes
                        st.success(f"Node {target_node.id} updated successfully.")
                        st.rerun()

                # Quick Actions for Selected Node
                col_btn_src, col_btn_snk = st.columns(2)
                with col_btn_src:
                    if st.button("Set as Source", use_container_width=True):
                        topo.set_source_node(target_node.id)
                        st.success(f"Node {target_node.id} designated as Source.")
                        st.rerun()
                with col_btn_snk:
                    if st.button("Set as Sink", use_container_width=True):
                        topo.set_sink_node(target_node.id)
                        st.success(f"Node {target_node.id} designated as Surface Sink.")
                        st.rerun()

                st.markdown("---")
                if st.button("Delete Selected Node", type="secondary", use_container_width=True):
                    topo.remove_node(target_node.id)
                    remaining = list(topo.nodes.keys())
                    st.session_state.selected_node_id = remaining[0] if remaining else None
                    st.warning(f"Node {target_node.id} and associated links deleted.")
                    st.rerun()
            else:
                st.info("No nodes in network. Add a node from the 'Add Node' tab.")

        # ---------------------------------------------------------
        # TAB 2: ADD NEW NODE
        # ---------------------------------------------------------
        with builder_tab2:
            st.markdown("#### Create New Node")
            # Suggest next available ID
            existing_ids = set(topo.nodes.keys())
            next_suggested_id = 1
            while next_suggested_id in existing_ids:
                next_suggested_id += 1

            with st.form("add_node_form"):
                new_id = st.number_input("Node ID:", min_value=1, max_value=999, value=next_suggested_id, step=1)
                new_name = st.text_input("Name:", value=f"Node {new_id}")
                new_type = st.selectbox("Role:", ["sensor", "source", "sink", "sensor_failed"])

                col_nx, col_ny = st.columns(2)
                with col_nx:
                    new_x = st.number_input("X (m):", value=200.0, step=20.0)
                with col_ny:
                    new_y = st.number_input("Y (m):", value=200.0, step=20.0)

                col_nz, col_nr = st.columns(2)
                with col_nz:
                    new_z = st.number_input("Elevation Z (m):", value=40.0, step=10.0)
                with col_nr:
                    new_range = st.number_input("Range (m):", value=250.0, step=25.0)

                new_energy = st.number_input("Initial Energy (J):", value=100.0, step=10.0)
                new_notes = st.text_input("Notes:", value="User added node")

                submit_add = st.form_submit_button("Add Node to Network", use_container_width=True)
                if submit_add:
                    if int(new_id) in topo.nodes:
                        st.error(f"Error: Node ID {new_id} already exists. Each node must have a unique integer ID.")
                    else:
                        new_node = Node(
                            node_id=int(new_id),
                            name=new_name,
                            node_type=new_type,
                            x=float(new_x),
                            y=float(new_y),
                            z=float(new_z),
                            initial_energy=float(new_energy),
                            tx_range=float(new_range),
                            status="Failed" if new_type == "sensor_failed" else "Operational",
                            notes=new_notes
                        )
                        topo.add_node(new_node)
                        st.session_state.selected_node_id = int(new_id)
                        st.success(f"Added Node {new_id} successfully.")
                        st.rerun()

        # ---------------------------------------------------------
        # TAB 3: LINK MANAGEMENT
        # ---------------------------------------------------------
        with builder_tab3:
            st.markdown("#### Acoustic Link Controls")

            col_autolink, col_clearlink = st.columns(2)
            with col_autolink:
                if st.button("Auto-Connect Reachable", use_container_width=True):
                    added_count = topo.auto_connect_reachable()
                    st.success(f"Connected {added_count} reachable acoustic links.")
                    st.rerun()
            with col_clearlink:
                if st.button("Clear All Links", use_container_width=True):
                    topo.clear_links()
                    st.warning("All acoustic links cleared.")
                    st.rerun()

            st.markdown("---")
            st.markdown("##### Manual Link Connection")
            if len(topo.nodes) >= 2:
                all_ids = sorted(list(topo.nodes.keys()))
                col_u, col_v = st.columns(2)
                with col_u:
                    link_u = st.selectbox("Node A:", all_ids, key="link_u_sel")
                with col_v:
                    # Filter out link_u
                    valid_v = [nid for nid in all_ids if nid != link_u]
                    link_v = st.selectbox("Node B:", valid_v, key="link_v_sel")

                dist_uv = topo.nodes[link_u].distance_to(topo.nodes[link_v])
                max_uv = min(topo.nodes[link_u].tx_range, topo.nodes[link_v].tx_range)
                is_reach = dist_uv <= max_uv

                st.caption(f"Euclidean Distance: **{dist_uv:.1f} m** | Range Threshold: **{max_uv:.1f} m** | Reachable: **{'YES' if is_reach else 'NO (Exceeds Range)'}**")

                col_add_l, col_rem_l = st.columns(2)
                with col_add_l:
                    if st.button("Add Link", use_container_width=True):
                        if topo.add_link(link_u, link_v):
                            st.success(f"Link {link_u} ↔ {link_v} added.")
                            st.rerun()
                        else:
                            st.info("Link already exists.")
                with col_rem_l:
                    if st.button("Remove Link", use_container_width=True):
                        if topo.remove_link(link_u, link_v):
                            st.warning(f"Link {link_u} ↔ {link_v} removed.")
                            st.rerun()
                        else:
                            st.info("Link does not exist.")
            else:
                st.info("At least 2 nodes are required to manage communication links.")

        # ---------------------------------------------------------
        # TAB 4: TEMPLATES & CONFIGURATION FILES
        # ---------------------------------------------------------
        with builder_tab4:
            st.markdown("#### Configuration Management")

            # 1. Quick Template Loader
            st.markdown("##### Pre-configured Topologies")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if st.button("Default Project (12-Node)", use_container_width=True):
                    st.session_state.current_topology = get_default_project_topology()
                    st.session_state.selected_node_id = 5
                    st.success("Loaded Authoritative 12-Node UWSN Topology.")
                    st.rerun()
            with col_t2:
                if st.button("Reset to Blank Network", use_container_width=True):
                    st.session_state.current_topology = NetworkTopology(name="Blank Network")
                    st.session_state.selected_node_id = None
                    st.warning("Reset to empty topology.")
                    st.rerun()

            st.markdown("---")
            # 2. Load from user_configs directory
            st.markdown("##### Load from Disk (`user_configs/`)")
            saved_configs = cfg_mgr.list_saved_configs()
            if saved_configs:
                config_options = [c["filename"] for c in saved_configs]
                selected_cfg = st.selectbox(
                    "Choose Configuration:",
                    config_options,
                    format_func=lambda fn: f"{fn} ({next(c['node_count'] for c in saved_configs if c['filename']==fn)} nodes)"
                )
                if st.button("Load Configuration", use_container_width=True):
                    loaded_topo, load_msg = cfg_mgr.load_config(selected_cfg)
                    if loaded_topo:
                        st.session_state.current_topology = loaded_topo
                        st.session_state.selected_node_id = next(iter(loaded_topo.nodes.keys()), None)
                        st.success(load_msg)
                        st.rerun()
                    else:
                        st.error(load_msg)
            else:
                st.info("No saved configurations found in `dashboard/user_configs/`.")

            st.markdown("---")
            # 3. Save current topology
            st.markdown("##### Save Current Network")
            with st.form("save_config_form"):
                save_name = st.text_input("Configuration File Name:", value=topo.name.lower().replace(" ", "_"))
                save_desc = st.text_input("Description:", value=topo.description)
                submit_save = st.form_submit_button("Save to JSON", use_container_width=True)
                if submit_save:
                    clean_name = save_name.strip()
                    if not clean_name:
                        st.error("Please enter a valid configuration name.")
                    else:
                        topo.name = save_name
                        topo.description = save_desc
                        success, save_msg, filepath = cfg_mgr.save_config(topo, clean_name)
                        if success:
                            st.success(save_msg)
                            st.rerun()
                        else:
                            st.error(save_msg)

            st.markdown("---")
            # 4. JSON Export & Import
            st.markdown("##### JSON Export & Import")
            json_str = json.dumps(topo.to_dict(), indent=2)
            st.download_button(
                label="Download JSON File",
                data=json_str,
                file_name=f"{topo.name.lower().replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )

            uploaded_file = st.file_uploader("Upload JSON Configuration", type=["json"], key="json_uploader")
            if uploaded_file is not None:
                try:
                    uploaded_data = json.load(uploaded_file)
                    imported_topo = NetworkTopology.from_dict(uploaded_data)
                    if st.button("Apply Uploaded Network", use_container_width=True):
                        st.session_state.current_topology = imported_topo
                        st.session_state.selected_node_id = next(iter(imported_topo.nodes.keys()), None)
                        st.success("Uploaded network imported successfully.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error parsing uploaded JSON: {e}")
