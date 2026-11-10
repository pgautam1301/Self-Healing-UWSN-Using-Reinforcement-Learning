"""
simulator_engine.py - Interactive Educational Demonstration Engine for UWSN Self-Healing.
Project: Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning
Module: Mode B Interactive Learning Simulator

Accurately demonstrates the 8-state, 3-action Q-learning self-healing mechanism
implemented in Aqua-Sim NG / NS-3.41 under Sensor 5 disruption at t = 50.0s.
All illustrative values in this module are clearly designated as educational demonstrations.
"""

import math
import numpy as np
import pandas as pd

# Standard Q-learning default hyperparameters from NS-3 implementation
DEFAULT_ALPHA = 0.1   # Learning rate
DEFAULT_GAMMA = 0.9   # Discount factor
DEFAULT_EPSILON = 0.1 # Exploration probability

# State Space: 8 discrete states defined by (faultLevel * 4) + (energyLevel * 2) + progressLevel
# faultLevel:    0 = Healthy (m_consecutiveTimeouts < 2), 1 = Degraded (m_consecutiveTimeouts >= 2)
# energyLevel:   0 = Low battery (< 30.0 J), 1 = High / Sufficient battery (>= 30.0 J)
# progressLevel: 0 = Non-positive progress (<= 0.0 m), 1 = Positive progress (> 0.0 m)

STATE_DEFINITIONS = {
    0: {
        'fault': 0, 'energy': 0, 'progress': 0,
        'label': 'S0: Healthy, Low Energy, Non-Positive Progress',
        'desc': 'Healthy channel, battery critical (<30J), lateral/no upward advancement. High drop risk.',
        'tag': 'Healthy / Critical'
    },
    1: {
        'fault': 0, 'energy': 0, 'progress': 1,
        'label': 'S1: Healthy, Low Energy, Positive Progress',
        'desc': 'Healthy channel, battery critical (<30J), viable upward advance toward sink.',
        'tag': 'Healthy / Low Batt'
    },
    2: {
        'fault': 0, 'energy': 1, 'progress': 0,
        'label': 'S2: Healthy, High Energy, Non-Positive Progress',
        'desc': 'Healthy channel, sufficient battery (>=30J), lateral candidate or no advancement.',
        'tag': 'Healthy / Lateral'
    },
    3: {
        'fault': 0, 'energy': 1, 'progress': 1,
        'label': 'S3: Healthy, High Energy, Positive Progress',
        'desc': 'Optimal normal operating state: healthy channel, ample battery, direct upward path.',
        'tag': 'Healthy / Optimal'
    },
    4: {
        'fault': 1, 'energy': 0, 'progress': 0,
        'label': 'S4: Degraded, Low Energy, Non-Positive Progress',
        'desc': 'Sector blocked (timeouts >= 2), critical battery, non-advancing angle. Avoid transmission.',
        'tag': 'Degraded / Critical'
    },
    5: {
        'fault': 1, 'energy': 0, 'progress': 1,
        'label': 'S5: Degraded, Low Energy, Positive Progress',
        'desc': 'Sector blocked (timeouts >= 2), low battery, viable upward angle. Defer to conserve power.',
        'tag': 'Degraded / Low Batt'
    },
    6: {
        'fault': 1, 'energy': 1, 'progress': 0,
        'label': 'S6: Degraded, High Energy, Non-Positive Progress',
        'desc': 'Sector blocked (timeouts >= 2), high battery, lateral candidate. Defer or search alternative pipe.',
        'tag': 'Degraded / Lateral'
    },
    7: {
        'fault': 1, 'energy': 1, 'progress': 1,
        'label': 'S7: Degraded, High Energy, Positive Progress',
        'desc': 'Sector blocked (timeouts >= 2), high battery, viable upward advance. Primary self-healing state (DEFER).',
        'tag': 'Degraded / Bypass Ready'
    }
}

ACTION_DEFINITIONS = {
    0: {
        'name': 'FORWARD (0)',
        'code': 'ACTION_FORWARD',
        'action_idx': 0,
        'desc': 'Immediate transmission: packet queued into CSMA MAC queue for contention.',
        'acoustic_delay': 0.0,
        'color': '#00E5FF'
    },
    1: {
        'name': 'DEFER (1)',
        'code': 'ACTION_DEFER',
        'action_idx': 1,
        'desc': 'Intentional acoustic backoff delay (0.5 s): yields channel to allow parallel spatial candidates to forward.',
        'acoustic_delay': 0.5,
        'color': '#F59E0B'
    },
    2: {
        'name': 'AVOID (2)',
        'code': 'ACTION_AVOID',
        'action_idx': 2,
        'desc': 'Local packet purge: packet dropped locally to prevent transmitting into confirmed dead-end void.',
        'acoustic_delay': 0.0,
        'color': '#EF4444'
    }
}


def calculate_reward_c(status, progress, trans_range=250.0, action=0, base_state=0):
    """
    Exact reproduction of reward logic in src/aqua-sim-ng/model/aqua-sim-routing-vbf.cc:
    - Terminal Sink ACK (status == 2): +20.0
    - Intermediate Relay ACK (status == 1): 5.0 + 5.0 * normProgress (bounded [5.0, 10.0])
    - ACK Timeout: -5.0
    - AVOID Action: Dynamic based on base state (baseState = rlState % 4)
    """
    if action == 2:  # RL_AVOID
        if base_state == 0:
            return 5.0   # Low energy, poor progress: optimal battery conservation
        elif base_state == 2:
            return 2.0   # High energy, poor progress: loop prevention
        elif base_state == 1:
            return -1.0  # Low energy, good progress: sacrificed viable advance
        elif base_state == 3:
            return -5.0  # High energy, good progress: faulty drop of viable packet
        return 0.0

    if status == 2:
        return 20.0  # Terminal Sink ACK
    elif status == 1:
        norm_progress = max(0.0, min(1.0, progress / trans_range)) if trans_range > 0 else 0.0
        return 5.0 + 5.0 * norm_progress
    elif status == -1:  # Timeout
        return -5.0
    return 0.0


def initialize_q_table():
    """Initializes standard 8x3 Q-table to 0.0."""
    q_table = {}
    for s in range(8):
        for a in range(3):
            q_table[(s, a)] = 0.0
    return q_table


def prewarm_q_table():
    """
    Generates a pre-warmed representative Q-table reflecting learned policy in P4:
    - In healthy states (S0-S3), FORWARD has highest Q-value.
    - In degraded states (S4-S7), DEFER and AVOID have higher Q-values.
    """
    q_table = initialize_q_table()
    # Healthy states bias toward FORWARD (0)
    q_table[(0, 0)] = 2.15; q_table[(0, 1)] = 0.85; q_table[(0, 2)] = 1.95
    q_table[(1, 0)] = 4.80; q_table[(1, 1)] = 1.20; q_table[(1, 2)] = -0.50
    q_table[(2, 0)] = 3.65; q_table[(2, 1)] = 2.10; q_table[(2, 2)] = 1.10
    q_table[(3, 0)] = 8.95; q_table[(3, 1)] = 3.40; q_table[(3, 2)] = -2.30

    # Degraded states (timeouts >= 2) bias toward DEFER (1) or AVOID (2)
    q_table[(4, 0)] = -3.20; q_table[(4, 1)] = 1.45; q_table[(4, 2)] = 3.80
    q_table[(5, 0)] = -1.80; q_table[(5, 1)] = 4.10; q_table[(5, 2)] = 0.60
    q_table[(6, 0)] = -2.50; q_table[(6, 1)] = 5.20; q_table[(6, 2)] = 2.30
    q_table[(7, 0)] = -1.10; q_table[(7, 1)] = 7.85; q_table[(7, 2)] = -0.80
    return q_table


# 9-Step Educational Simulation Script
EDUCATIONAL_STEPS = [
    {
        'step_num': 1,
        'title': '1. Application Traffic Generation at Seafloor',
        'actor': 'Source (Node 12)',
        'actor_id': 12,
        'time': 't = 48.0s (Pre-Failure)',
        'network_phase': 'Normal Pre-Failure Operation',
        'active_nodes': [12, 1],
        'packet_path': [(12, 1)],
        'active_edge': (12, 1),
        's5_status': 'Operational (Remaining: 74.5 J)',
        'consecutive_timeouts': 0,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'Packet Injected',
        'event_summary': 'Source Node 12 generates CBR Data Packet UID 100 on the seafloor (50, 50, 0) and broadcasts upward along the vector toward the surface sink.',
        'detailed_explanation': (
            "The seafloor source operates an OnOff CBR application generating 40-byte acoustic packets. "
            "Acoustic carrier propagation travels at 1500 m/s through the underwater column. "
            "First-hop relay Sensor 1 receives the acoustic transmission cleanly."
        ),
        'bellman_math': None
    },
    {
        'step_num': 2,
        'title': '2. Normal Intermediate Forwarding via Sensor 4',
        'actor': 'Sensor 4 (Node 4)',
        'actor_id': 4,
        'time': 't = 49.2s (Pre-Failure)',
        'network_phase': 'Normal Pre-Failure Operation',
        'active_nodes': [1, 4],
        'packet_path': [(12, 1), (1, 4)],
        'active_edge': (1, 4),
        's5_status': 'Operational (Remaining: 73.1 J)',
        'consecutive_timeouts': 0,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'State Evaluated: S3 (Healthy)',
        'event_summary': 'Sensor 4 receives the packet. It evaluates its Q-learning state: battery is 72.5 J (>=30 J), timeouts = 0, progress = +40 m upward toward sink -> State S3.',
        'detailed_explanation': (
            "In State 3 (Healthy, High Energy, Positive Progress), the learned Q-table dictates ACTION_FORWARD (0). "
            "Sensor 4 immediately enqueues the packet, transmits into the acoustic corridor, and starts its 1.0s ACK timeout timer."
        ),
        'bellman_math': None
    },
    {
        'step_num': 3,
        'title': '3. Downstream Reception & Reverse ACK Confirmation',
        'actor': 'Sensor 5 (Node 5)',
        'actor_id': 5,
        'time': 't = 49.8s (Pre-Failure)',
        'network_phase': 'Normal Pre-Failure Operation',
        'active_nodes': [4, 5],
        'packet_path': [(12, 1), (1, 4), (4, 5)],
        'active_edge': (4, 5),
        's5_status': 'Operational (Remaining: 72.21 J)',
        'consecutive_timeouts': 0,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'RL Reverse ACK Sent (Status=1)',
        'event_summary': 'Sensor 5 receives the packet, forwards upward, and transmits an asynchronous Layer-3 Reverse ACK (Status=1) back to forwarder Sensor 4.',
        'detailed_explanation': (
            "Upon receiving the ACK, Sensor 4 resets m_consecutiveTimeouts to 0, cancels its timeout timer, "
            "and receives a positive reward: R = 5.0 + 5.0 * (normProgress) = +7.80. Q(3, FORWARD) increases."
        ),
        'bellman_math': {
            'state': 3, 'action': 0, 'reward': 7.80, 'next_state': 3,
            'current_q': 8.95, 'max_next_q': 8.95, 'alpha': 0.1, 'gamma': 0.9,
            'delta': 7.80 + 0.9 * 8.95 - 8.95,
            'new_q': 8.95 + 0.1 * (7.80 + 0.9 * 8.95 - 8.95)
        }
    },
    {
        'step_num': 4,
        'title': '4. Scheduled Sensor 5 Disruption (t = 50.0s)',
        'actor': 'Simulator Scheduler',
        'actor_id': 5,
        'time': 't = 50.0s (FAULT EVENT)',
        'network_phase': 'Sensor Failure Scheduled Event',
        'active_nodes': [5],
        'packet_path': [],
        'active_edge': None,
        's5_status': 'FAILED / DEAD (Residual Energy HALTED at 72.21 J)',
        'consecutive_timeouts': 0,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'Transceiver Halted',
        'event_summary': 'NS-3 Simulator executes Simulator::Schedule(Seconds(50.0), &FailSensor). Sensor 5 transceiver completely ceases transmission and reception.',
        'detailed_explanation': (
            "Sensor 5's battery consumption immediately freezes at exactly 72.21 J (verified across all 10 P4 multi-seed runs). "
            "An acoustic communication black hole is now created directly along the primary forwarding corridor between depth 58m and surface."
        ),
        'bellman_math': None
    },
    {
        'step_num': 5,
        'title': '5. Subsequent Transmission & Missing Downstream ACK',
        'actor': 'Sensor 4 (Node 4)',
        'actor_id': 4,
        'time': 't = 50.8s (Post-Failure)',
        'network_phase': 'Post-Failure Packet Attempt',
        'active_nodes': [4],
        'packet_path': [(1, 4)],
        'active_edge': (4, 5),
        's5_status': 'FAILED (No Response)',
        'consecutive_timeouts': 0,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'Transmitted into Void; Waiting ACK...',
        'event_summary': 'Sensor 4 receives new Packet UID 101 from seafloor and transmits toward Sensor 5. Sensor 4 starts its 1.0s acoustic ACK timeout timer.',
        'detailed_explanation': (
            "Because Sensor 5 is dead, it cannot decode the packet or generate an ACK. "
            "In static protocols (e.g. Forced VBF), Sensor 4 would retransmit into the dead node repeatedly, wasting valuable joules."
        ),
        'bellman_math': None
    },
    {
        'step_num': 6,
        'title': '6. First ACK Timeout at Sensor 4 (Counter = 1)',
        'actor': 'Sensor 4 (Node 4)',
        'actor_id': 4,
        'time': 't = 51.8s (Post-Failure)',
        'network_phase': 'Timeout Detection',
        'active_nodes': [4],
        'packet_path': [],
        'active_edge': None,
        's5_status': 'FAILED (Zero Transceiver Activity)',
        'consecutive_timeouts': 1,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'AckTimeout() Fired: Penalty = -5.0',
        'event_summary': 'ACK timeout timer expires. Sensor 4 invokes AckTimeout(): increments m_consecutiveTimeouts to 1, applies penalty R = -5.0.',
        'detailed_explanation': (
            "Notice the implementation detail: faultLevel = (m_consecutiveTimeouts >= 2) ? 1 : 0. "
            "With 1 timeout, faultLevel is still 0. Sensor 4 remains in State 3, but Q(3, FORWARD) is reduced. "
            "A second timeout will trigger the transition to Degraded State 7."
        ),
        'bellman_math': {
            'state': 3, 'action': 0, 'reward': -5.0, 'next_state': 3,
            'current_q': 8.95, 'max_next_q': 8.95, 'alpha': 0.1, 'gamma': 0.9,
            'delta': -5.0 + 0.9 * 8.95 - 8.95,
            'new_q': 8.95 + 0.1 * (-5.0 + 0.9 * 8.95 - 8.95)
        }
    },
    {
        'step_num': 7,
        'title': '7. Second Timeout & State Transition to Degraded State 7',
        'actor': 'Sensor 4 (Node 4)',
        'actor_id': 4,
        'time': 't = 53.0s (Post-Failure)',
        'network_phase': 'Degraded State Activation',
        'active_nodes': [4],
        'packet_path': [],
        'active_edge': None,
        's5_status': 'FAILED (Confirmed Sector Blockage)',
        'consecutive_timeouts': 2,
        'state_idx': 7,
        'action_idx': 1,
        'status_feedback': 'State Transition: S3 -> S7 (Degraded)',
        'event_summary': 'A second consecutive timeout increments m_consecutiveTimeouts to 2. faultLevel becomes 1! Sensor 4 transitions to Degraded State 7.',
        'detailed_explanation': (
            "State 7 formula: (1 * 4) + (1 * 2) + 1 = 7. "
            "In State 7, the Q-table policy dictates ACTION_DEFER (1) instead of FORWARD. "
            "Crucially, Sensor 4 does NOT know Sensor 5 specifically died; it detects that its downstream forwarding sector is failing!"
        ),
        'bellman_math': {
            'state': 3, 'action': 0, 'reward': -5.0, 'next_state': 7,
            'current_q': 8.35, 'max_next_q': 7.85, 'alpha': 0.1, 'gamma': 0.9,
            'delta': -5.0 + 0.9 * 7.85 - 8.35,
            'new_q': 8.35 + 0.1 * (-5.0 + 0.9 * 7.85 - 8.35)
        }
    },
    {
        'step_num': 8,
        'title': '8. Acoustic Deferral & Spatial Candidate Bypass',
        'actor': 'Sensors 4, 6, and 7',
        'actor_id': 6,
        'time': 't = 53.5s (Self-Healing Activation)',
        'network_phase': 'Spatial Candidate Bypass',
        'active_nodes': [4, 6, 7],
        'packet_path': [(1, 4), (4, 6), (6, 7)],
        'active_edge': (4, 6),
        's5_status': 'BYPASSED via Lateral Route',
        'consecutive_timeouts': 2,
        'state_idx': 7,
        'action_idx': 1,
        'status_feedback': 'Sensor 4 Defers (0.5s); Sensor 6 Forwards!',
        'event_summary': 'Sensor 4 executes ACTION_DEFER (1), remaining silent for 0.5s. Parallel candidate Sensor 6 (in healthy State 3) overhears and executes FORWARD!',
        'detailed_explanation': (
            "This is the core emergent self-healing mechanism: VBF's routing cylinder (width W = 100m, range 250m) encompasses multiple lateral candidates. "
            "While Sensor 4 voluntarily yields the acoustic channel, Sensor 6 (at 290, 290, 50m) forwards the packet, routing cleanly around the dead Sensor 5."
        ),
        'bellman_math': None
    },
    {
        'step_num': 9,
        'title': '9. Terminal Delivery to Surface Gateway & Parity Verified',
        'actor': 'Surface Sink (Node 11)',
        'actor_id': 11,
        'time': 't = 54.8s (Delivered)',
        'network_phase': 'Self-Healing Verified',
        'active_nodes': [6, 7, 8, 11],
        'packet_path': [(12, 1), (1, 4), (4, 6), (6, 7), (7, 8), (8, 11)],
        'active_edge': (8, 11),
        's5_status': 'Dead node bypassed with parity',
        'consecutive_timeouts': 0,
        'state_idx': 3,
        'action_idx': 0,
        'status_feedback': 'Terminal Delivery Verified (Reward = +20.0)',
        'event_summary': 'Packet reaches Surface Gateway Sink (Node 11). Sink sends terminal ACK (Status=2). Delivery parity is confirmed (62.50% vs 63.53%, p=0.364)!',
        'detailed_explanation': (
            "Sensor 8 receives +20.0 terminal reward. When reverse confirmation reaches Sensor 4 via overhearing, its failure counter resets. "
            "P4 achieved self-healing without global flooding or packet duplication, saving 35.90 J of energy compared to Forced VBF."
        ),
        'bellman_math': {
            'state': 3, 'action': 0, 'reward': 20.0, 'next_state': 3,
            'current_q': 8.95, 'max_next_q': 8.95, 'alpha': 0.1, 'gamma': 0.9,
            'delta': 20.0 + 0.9 * 8.95 - 8.95,
            'new_q': 8.95 + 0.1 * (20.0 + 0.9 * 8.95 - 8.95)
        }
    }
]


def step_simulation(step_index):
    """Returns the scenario state for the requested step index (0 to 8)."""
    idx = max(0, min(len(EDUCATIONAL_STEPS) - 1, step_index))
    return EDUCATIONAL_STEPS[idx]


def execute_q_learning_update(current_q_table, state, action, reward, next_state, alpha=DEFAULT_ALPHA, gamma=DEFAULT_GAMMA):
    """
    Executes real Bellman update on the provided Q-table:
    Q(s, a) = Q(s, a) + alpha * [ r + gamma * max_a' Q(s', a') - Q(s, a) ]
    Returns (updated_q_table, step_math_dict).
    """
    q_table = dict(current_q_table)
    cur_q = q_table.get((state, action), 0.0)
    max_next_q = max(q_table.get((next_state, a_next), 0.0) for a_next in range(3))
    target = reward + gamma * max_next_q
    delta = target - cur_q
    new_q = cur_q + alpha * delta
    q_table[(state, action)] = round(new_q, 4)

    math_breakdown = {
        'state': state,
        'action': action,
        'reward': reward,
        'next_state': next_state,
        'current_q': cur_q,
        'max_next_q': max_next_q,
        'target': target,
        'delta': delta,
        'new_q': new_q,
        'alpha': alpha,
        'gamma': gamma
    }
    return q_table, math_breakdown
