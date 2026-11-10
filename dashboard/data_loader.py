"""
data_loader.py - Data ingestion, validation, and preprocessing for UWSN Demonstration Simulator.
Loads verified P6.4 multi-seed experimental data, topology configurations, and actual NS-3 simulation logs.
"""

import os
import re
import math
import pandas as pd
import numpy as np
import streamlit as st

# Protocol metadata mapping
PROTOCOL_NAMES = {
    'p4': 'P4 Fault-Aware RL',
    'p2': 'P2 Original RL',
    'vbf': 'Forced-Forward VBF',
    'dbr': 'Pure DBR',
    'eedbr': 'EEDBR (Wahid 2011)'
}

PROTOCOL_COLORS = {
    'p4': '#00E5FF',     # Bright Cyan / Aqua
    'p2': '#3B82F6',     # Royal Blue
    'vbf': '#F59E0B',    # Amber / Orange
    'dbr': '#8B5CF6',    # Violet / Purple
    'eedbr': '#10B981'   # Emerald Green
}

# Metric labels, units, and descriptions
METRIC_DEFINITIONS = {
    'unique_pdr': {
        'label': 'Unique-Packet PDR',
        'unit': '%',
        'desc': 'Percentage of unique packets injected by source that were successfully delivered to sink.',
        'format': '{:.2f}%'
    },
    'pre_unique_pdr': {
        'label': 'Pre-Failure Unique PDR (<50s)',
        'unit': '%',
        'desc': 'Unique packet delivery ratio during normal operation prior to Sensor 5 failure (154 packets).',
        'format': '{:.2f}%'
    },
    'post_unique_pdr': {
        'label': 'Post-Failure Unique PDR (>=50s)',
        'unit': '%',
        'desc': 'Unique packet delivery ratio under Sensor 5 failure condition (156 packets).',
        'format': '{:.2f}%'
    },
    'total_pdr': {
        'label': 'Total Reception Ratio (Duplicate-Inclusive)',
        'unit': '%',
        'desc': 'Total sink packet receptions (including duplicate copies) divided by injected packets. Multi-copy reception ratio, not conventional PDR.',
        'format': '{:.2f}%'
    },
    'mean_delay': {
        'label': 'Mean End-to-End Delay',
        'unit': 's',
        'desc': 'Average transmission delay across all unique delivered packets evaluated at first arrival.',
        'format': '{:.4f} s'
    },
    'p95_delay': {
        'label': '95th Percentile Delay',
        'unit': 's',
        'desc': '95th percentile end-to-end delay representing acoustic tail latency.',
        'format': '{:.4f} s'
    },
    'total_energy': {
        'label': 'Total Sensor Energy Consumed',
        'unit': 'J',
        'desc': 'Total acoustic energy expended across all 10 underwater sensors (Sensors 1-10).',
        'format': '{:.2f} J'
    },
    'energy_per_unique': {
        'label': 'Energy per Unique Delivered Packet',
        'unit': 'J/pkt',
        'desc': 'Total energy expended divided by unique packets successfully delivered to sink.',
        'format': '{:.4f} J/pkt'
    },
    's5_residual': {
        'label': 'Sensor 5 Residual Energy',
        'unit': 'J',
        'desc': 'Remaining battery energy of Sensor 5 after scheduled failure at t = 50.0s (initial 100 J).',
        'format': '{:.2f} J'
    },
    'control_overhead': {
        'label': 'Control Overhead',
        'unit': 'pkts',
        'desc': 'Protocol control packets (RL ACKs for P4/P2, Startup depth beacons for DBR, Periodic beacons for EEDBR).',
        'format': '{:d} pkts'
    }
}


def find_data_file(filename):
    """Find file in common paths relative to script location."""
    candidates = [
        filename,
        os.path.join("..", filename),
        os.path.join(os.path.dirname(__file__), "..", filename),
        os.path.join(os.path.dirname(__file__), filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


@st.cache_data(show_spinner=False)
def load_per_run_data():
    """
    Load and validate P6.4 per-run results CSV.
    Validates that exactly 50 records exist across 5 protocols.
    """
    csv_path = find_data_file("results_p6/P6_4_per_run_results.csv")
    if not csv_path:
        raise FileNotFoundError(
            "Could not locate 'results_p6/P6_4_per_run_results.csv'. "
            "Please ensure the dashboard is run from the project root or dashboard directory."
        )

    df = pd.read_csv(csv_path)

    # Validate required columns
    required_cols = [
        'protocol', 'run', 'total_injected', 'total_delivered',
        'unique_delivered', 'total_pdr', 'unique_pdr',
        'pre_injected', 'pre_delivered', 'pre_unique_pdr',
        'post_injected', 'post_delivered', 'post_unique_pdr',
        'mean_delay', 'median_delay', 'p95_delay',
        'total_energy', 'energy_per_total', 'energy_per_unique',
        's5_consumed', 's5_residual', 'control_overhead'
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}")

    df['protocol_name'] = df['protocol'].map(PROTOCOL_NAMES).fillna(df['protocol'])
    return df


@st.cache_data(show_spinner=False)
def load_summary_statistics():
    """Load precalculated summary statistics CSV if available."""
    csv_path = find_data_file("results_p6/P6_4_summary_statistics.csv")
    if not csv_path:
        return None
    return pd.read_csv(csv_path)


def get_topology_nodes():
    """
    Returns exact node coordinates and attributes from scratch/underwater-network.cc.
    Reflected underwater coordinates: z_new = 100 - z_old.
    Source: (50, 50, 0)
    Sensors 1-10: (90 + i*40, 90 + i*40, 10 + i*8)
    Sink: (500, 500, 100) (Sea surface)
    """
    nodes = [
        {
            'id': 12,
            'name': 'Source Node (Node 12)',
            'short_name': 'Source',
            'type': 'source',
            'x': 50.0,
            'y': 50.0,
            'z': 0.0,
            'depth_desc': 'Seafloor Source (0.0 m reflected elevation, 100 m depth)',
            'status': 'Operational',
            'role': 'Data Generator (1 kbps, 40 B pkts)'
        }
    ]

    for i in range(10):
        sensor_num = i + 1
        x = 90.0 + i * 40.0
        y = 90.0 + i * 40.0
        z = 10.0 + i * 8.0
        is_s5 = (sensor_num == 5)
        
        nodes.append({
            'id': sensor_num,
            'name': f'Sensor {sensor_num} (Node {sensor_num})',
            'short_name': f'Sensor {sensor_num}',
            'type': 'sensor_failed' if is_s5 else 'sensor',
            'x': x,
            'y': y,
            'z': z,
            'depth_desc': f'{z:.1f} m elevation ({100.0 - z:.1f} m depth)',
            'status': 'Scheduled Failure at 50.0s' if is_s5 else 'Operational',
            'role': 'Intermediate Relay / Router'
        })

    nodes.append({
        'id': 11,
        'name': 'Sink Node (Node 11)',
        'short_name': 'Sink',
        'type': 'sink',
        'x': 500.0,
        'y': 500.0,
        'z': 100.0,
        'depth_desc': 'Surface Buoy / Gateway (100.0 m elevation, 0 m depth)',
        'status': 'Operational',
        'role': 'Data Collector'
    })

    return nodes


def get_potential_acoustic_links(tx_range=250.0):
    """
    Calculates potential acoustic connectivity links where Euclidean distance <= tx_range.
    Explicitly labeled as potential acoustic coverage links, not active routing paths.
    """
    nodes = get_topology_nodes()
    links = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            n1, n2 = nodes[i], nodes[j]
            dx = n1['x'] - n2['x']
            dy = n1['y'] - n2['y']
            dz = n1['z'] - n2['z']
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            if dist <= tx_range:
                involves_s5 = (n1['short_name'] == 'Sensor 5' or n2['short_name'] == 'Sensor 5')
                links.append({
                    'node1': n1,
                    'node2': n2,
                    'distance': dist,
                    'involves_s5': involves_s5
                })

    return links


@st.cache_data(show_spinner=False)
def load_actual_simulation_trace(run_num=1):
    """
    Parses actual simulation log from results_p6/p4_run{:02d}.log in chronological order.
    Extracts real timestamps, packet UIDs, states, actions, ACKs, timeouts, and failure events.
    Returns:
        dict containing:
            'events_df': DataFrame of chronological events
            'total_events': int
            'sink_deliveries': int
            'unique_deliveries': int
            'timeouts_count': int
            'acks_count': int
    """
    filename = f"results_p6/p4_run{run_num:02d}.log"
    log_path = find_data_file(filename)
    if not log_path and run_num == 1:
        log_path = find_data_file("results_p6/p4_run1.log")
        
    if not log_path:
        return None

    events = []
    cur_time = 0.0
    delivered_uids = set()
    total_sink_receptions = 0

    with open(log_path, 'r', errors='ignore') as f:
        for line_num, line in enumerate(f):
            # Parse source transmission
            m_t = re.search(r'\[SOURCE-TX\].*Time=([\d\.]+)', line)
            if m_t:
                cur_time = float(m_t.group(1))
                m_uid = re.search(r'Packet UID=(\d+)', line)
                uid = int(m_uid.group(1)) if m_uid else -1
                events.append({
                    'time': cur_time,
                    'event_type': 'SOURCE_TX',
                    'node_id': 12,
                    'node_name': 'Source (Node 12)',
                    'target_id': 1,
                    'packet_uid': uid,
                    'state': None,
                    'action': 0,
                    'reward': None,
                    'q_value': None,
                    'timeouts': 0,
                    'description': f'Source injected Packet UID {uid} into acoustic channel',
                    'phase': 'Pre-Failure' if cur_time < 50.0 else 'Post-Failure',
                    'line_num': line_num
                })

            # Update clock from MAC layer transmission
            m_mactx = re.search(r'MACsend: delay \d+ at time ([\d\.]+)', line)
            if m_mactx:
                cur_time = float(m_mactx.group(1))

            # Scheduled sensor failure event
            if '*** SENSOR FAILURE ***' in line:
                events.append({
                    'time': 50.0,
                    'event_type': 'SENSOR_FAILURE',
                    'node_id': 5,
                    'node_name': 'Sensor 5 (Node 5)',
                    'target_id': None,
                    'packet_uid': None,
                    'state': None,
                    'action': None,
                    'reward': None,
                    'q_value': None,
                    'timeouts': None,
                    'description': '*** SENSOR 5 FAILURE *** Transceiver halted deterministically at 50.0s',
                    'phase': 'Fault Injection Event',
                    'line_num': line_num
                })

            # RL experience stored
            m_exp = re.search(r'RL Experience Stored: Node=(\d+) Packet=(\d+) State=(\d+) Action=(\d+)', line)
            if m_exp:
                n_id = int(m_exp.group(1))
                p_uid = int(m_exp.group(2))
                st_id = int(m_exp.group(3))
                act_id = int(m_exp.group(4))
                act_str = 'FORWARD' if act_id == 0 else ('DEFER' if act_id == 1 else 'AVOID')
                events.append({
                    'time': cur_time,
                    'event_type': 'RL_DECISION',
                    'node_id': n_id,
                    'node_name': f'Sensor {n_id}',
                    'target_id': None,
                    'packet_uid': p_uid,
                    'state': st_id,
                    'action': act_id,
                    'reward': None,
                    'q_value': None,
                    'timeouts': None,
                    'description': f'Sensor {n_id} evaluated Packet {p_uid}: State S{st_id} -> Action {act_str}',
                    'phase': 'Pre-Failure' if cur_time < 50.0 else 'Post-Failure',
                    'line_num': line_num
                })

            # RL feedback sent
            m_fb = re.search(r'RL Feedback Sent: Forwarder=(\d+) Receiver=(\d+) Packet=(\d+) Status=(\d+)', line)
            if m_fb:
                fwd = int(m_fb.group(1))
                rec = int(m_fb.group(2))
                pkt = int(m_fb.group(3))
                status = int(m_fb.group(4))
                is_terminal = (status == 2)
                if is_terminal and rec == 11:
                    total_sink_receptions += 1
                    delivered_uids.add(pkt)
                status_label = 'Terminal Sink ACK' if is_terminal else 'Intermediate Relay ACK'
                events.append({
                    'time': cur_time,
                    'event_type': 'SINK_DELIVERY' if is_terminal else 'RELAY_ACK',
                    'node_id': rec,
                    'node_name': 'Sink (Node 11)' if rec == 11 else f'Sensor {rec}',
                    'target_id': fwd,
                    'packet_uid': pkt,
                    'state': None,
                    'action': None,
                    'reward': 20.0 if is_terminal else None,
                    'q_value': None,
                    'timeouts': None,
                    'description': f'Node {rec} transmitted {status_label} to Node {fwd} for Packet {pkt}',
                    'phase': 'Pre-Failure' if cur_time < 50.0 else 'Post-Failure',
                    'line_num': line_num
                })

            # RL learning update (positive or progress reinforcement)
            m_upd = re.search(r'RL Learning Update: Node=(\d+) Packet=(\d+) Action=(\d+) Status=(\d+) Reward=([\d\.\-]+) New Q-value=([\d\.\-]+)', line)
            if m_upd:
                n_id = int(m_upd.group(1))
                p_uid = int(m_upd.group(2))
                act_id = int(m_upd.group(3))
                rew = float(m_upd.group(5))
                new_q = float(m_upd.group(6))
                events.append({
                    'time': cur_time,
                    'event_type': 'RL_BELLMAN_UPDATE',
                    'node_id': n_id,
                    'node_name': f'Sensor {n_id}',
                    'target_id': None,
                    'packet_uid': p_uid,
                    'state': None,
                    'action': act_id,
                    'reward': rew,
                    'q_value': new_q,
                    'timeouts': 0,
                    'description': f'Sensor {n_id} Bellman update: Reward={rew:+.2f}, New Q={new_q:.4f}',
                    'phase': 'Pre-Failure' if cur_time < 50.0 else 'Post-Failure',
                    'line_num': line_num
                })

            # RL ACK Timeout (negative reinforcement)
            m_to = re.search(r'RL ACK Timeout: Node=(\d+) Packet=(\d+) Action=(\d+) Penalty=([\d\.\-]+) ConsecutiveTimeouts=(\d+) New Q-value=([\d\.\-]+)', line)
            if m_to:
                n_id = int(m_to.group(1))
                p_uid = int(m_to.group(2))
                act_id = int(m_to.group(3))
                pen = float(m_to.group(4))
                consec = int(m_to.group(5))
                new_q = float(m_to.group(6))
                events.append({
                    'time': cur_time,
                    'event_type': 'ACK_TIMEOUT',
                    'node_id': n_id,
                    'node_name': f'Sensor {n_id}',
                    'target_id': None,
                    'packet_uid': p_uid,
                    'state': None,
                    'action': act_id,
                    'reward': pen,
                    'q_value': new_q,
                    'timeouts': consec,
                    'description': f'Sensor {n_id} ACK Timeout! Penalty={pen:+.1f}, ConsecutiveTimeouts={consec}, New Q={new_q:.4f}',
                    'phase': 'Pre-Failure' if cur_time < 50.0 else 'Post-Failure',
                    'line_num': line_num
                })

    # Sort events by physical simulation time and line occurrence
    events.sort(key=lambda x: (x['time'], x['line_num']))
    df_events = pd.DataFrame(events)

    return {
        'events_df': df_events,
        'total_events': len(df_events),
        'total_deliveries': total_sink_receptions,
        'unique_deliveries': len(delivered_uids),
        'delivered_uids': delivered_uids
    }
