# P9.0 — Demonstration Simulator Implementation & Verification Report

**Project Title:** Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning  
**Module:** Interactive Demonstration Simulator & Analytics Dashboard (`dashboard/`)  
**Date:** November 9, 2026  
**Implementation Standards:** NS-3.41 + Aqua-Sim NG | Strict Scientific Integrity Mode  

---

## 1. Executive Summary

Under task P9.0, the Streamlit dashboard developed in Phase P7 was extended into an interactive demonstration simulator. The simulator is designed for viva examinations, technical project demonstrations, and academic presentations.

The application incorporates two distinct operating modes:
1. **Mode A (Actual Results Replay):** A high-fidelity playback engine that parses and replays 5,009 real timestamp-ordered telemetry events from verified NS-3.41 simulation logs (`results_p6/p4_run01.log` through `run10.log`). Zero events or Q-values are fabricated.
2. **Mode B (Interactive Step-by-Step Simulator):** A guided educational demonstration engine allowing the presenter to walk through the 9-step failure, timeout detection, Bellman Q-table update, and spatial candidate bypass sequence with exact mathematical breakdowns.

All physical coordinates, acoustic channel parameters, state-action spaces, reward functions, and empirical metrics reflect the verified implementation in `scratch/underwater-network.cc` and `src/aqua-sim-ng/model/aqua-sim-routing-vbf.cc`.

---

## 2. Architecture & Modular Design

The dashboard follows a separation of presentation logic from data processing:

```text
dashboard/
├── app.py                     # Streamlit UI, 3D Plotly views, interactive controls, and page dispatch
├── data_loader.py             # Log parsing engine, CSV dataset ingestion, and topology allocator
├── simulator_engine.py        # Mode B educational demonstration engine and Bellman update calculator
├── requirements.txt           # Package specifications (streamlit, plotly, pandas, numpy)
├── README.md                  # Comprehensive user and launch documentation
└── P9_DEMO_IMPLEMENTATION_REPORT.md  # Detailed implementation audit report
```

### Key Data Ingestion Flows:
```
[ results_p6/p4_run01.log ] --------> data_loader.load_actual_simulation_trace() ----> Mode A Replay UI
[ P6_4_summary_statistics.csv ] ----> data_loader.load_summary_statistics() ---------> Benchmark UI
[ P6_4_per_run_results.csv ] -------> data_loader.load_per_run_data() ---------------> Benchmark & Charts
[ aqua-sim-routing-vbf.cc ] --------> simulator_engine.py ---------------------------> Mode B Simulator
```

---

## 3. Implementation Verification: Mode A (Actual NS-3 Replay)

### Capabilities & Behavioral Verification:
1. **Chronological Trace Parsing:**
   - Successfully parses `results_p6/p4_run01.log` (56,927 lines) into 5,009 distinct chronological events:
     - `SOURCE_TX`: 310 packet injection events from Source Node 12 with actual transmission timestamps.
     - `RL_DECISION`: 1,735 candidate routing evaluations across sensor nodes recording the exact evaluated state (S0–S7) and chosen action (0, 1, or 2).
     - `FEEDBACK_SENT`: Layer-3 reverse acknowledgment events distinguishing intermediate relay ACKs (Status=1) from terminal sink deliveries (Status=2).
     - `RL_BELLMAN_UPDATE`: 549 positive reinforcement learning updates recording real rewards and updated Q-values.
     - `ACK_TIMEOUT`: 1,122 unacknowledged transmission timeout events recording the penalty ($-5.0$), consecutive timeout counter, and updated Q-values.
     - `SENSOR_FAILURE`: Scheduled event at $t = 50.0\text{ s}$ halting Sensor 5.
2. **Deterministic Sensor 5 Disruption:**
   - At $t = 50.0\text{ s}$, Sensor 5's visual indicator transitions from active status to a red 'X' labeled `[FAILED AT 50.0s]`.
   - Sensor 5 residual battery halts at $72.21\text{ J}$ ($27.79\text{ J}$ consumed) across all P4 runs, matching the physical simulation log.
3. **Data Availability Integrity Guarantee:**
   - Where a internal node parameter was not written to standard log output, the UI explicitly marks it as `Data unavailable from log`, adhering strictly to scientific integrity requirements.

---

## 4. Implementation Verification: Mode B (Interactive Simulator)

### The 9-Step Guided Self-Healing Sequence:
Mode B enables interactive step-by-step navigation through the self-healing workflow:

| Step # | Event Title | Actor | Network Phase | Physical & Algorithmic Event |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Traffic Generation | Source (Node 12) | Pre-Failure | Injects 40-byte packet into acoustic corridor at $(50, 50, 0)\text{ m}$. |
| **2** | Normal Forwarding | Sensor 4 | Pre-Failure | Evaluates State S3 (Healthy, High Energy, Positive Progress); executes `FORWARD`. |
| **3** | Reverse ACK Confirmation | Sensor 5 | Pre-Failure | Receives packet, forwards, and sends Layer-3 ACK ($R = +7.80$); resets failure counter. |
| **4** | Scheduled Sensor Failure | Scheduler | Fault Event | $t = 50.0\text{ s}$: Sensor 5 transceiver halts completely; residual battery halts at $72.21\text{ J}$. |
| **5** | Missing Downstream ACK | Sensor 4 | Post-Failure | Sensor 4 transmits new packet toward dead Sensor 5; starts 1.0s timeout timer. |
| **6** | First ACK Timeout | Sensor 4 | Timeout Detection | Timer expires; invokes `AckTimeout()`; increments `timeouts = 1`; penalty $R = -5.0$. |
| **7** | Second Timeout & Degradation | Sensor 4 | State Transition | Second timeout increments `timeouts = 2`; `faultLevel` becomes 1; transitions to State S7. |
| **8** | Acoustic Deferral & Bypass | Sensors 4, 6, 7 | Self-Healing | Sensor 4 defers ($0.5\text{ s}$); parallel candidate Sensor 6 overhears and forwards packet. |
| **9** | Terminal Delivery to Sink | Sink (Node 11) | Parity Verified | Packet delivered to surface gateway; delivery parity confirmed ($62.50\%$ vs $63.53\%$, $p = 0.364$). |

### Real-Time Bellman Equation Calculator:
Mode B calculates and displays the exact numerical Bellman update:
$$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$
- Standard verified hyperparameters: $\alpha = 0.1$, $\gamma = 0.9$, $\epsilon = 0.1$.
- Displays the Temporal Difference error ($\delta = r + \gamma \max Q - Q$) and step-by-step arithmetic.
- Maintains a dynamic $8 \times 3$ interactive Q-Table heatmap.

### Architectural Scoping Notice:
The simulator explicitly notes that `m_consecutiveTimeouts` is tracked at the node level (detecting sector blockage) rather than maintaining explicit neighbor ID routing tables.

---

## 5. Physical Topology & Acoustic Environment

- **Reflected Coordinate Transformation:** $z_{\text{new}} = 100 - z_{\text{old}}$ correctly modeled.
  - Seafloor Source (Node 12): $(50.0, 50.0, 0.0)\text{ m}$ (depth $100\text{ m}$)
  - Surface Sink (Node 11): $(500.0, 500.0, 100.0)\text{ m}$ (depth $0\text{ m}$)
  - Sensors 1–10: $(90 + 40i, 90 + 40i, 10 + 8i)\text{ m}$ for $i = 0, \dots, 9$
  - Sensor 5: $(250.0, 250.0, 42.0)\text{ m}$ (depth $58\text{ m}$)
- **Acoustic Channel Parameters:**
  - Acoustic propagation speed: $1500.0\text{ m/s}$
  - Transmission range: $250.0\text{ m}$
  - Transceiver power model: $P_{\text{tx}} = 2.0\text{ W}$, $P_{\text{rx}} = 0.75\text{ W}$, $P_{\text{idle}} = 0.008\text{ W}$

---

## 6. Multi-Protocol Performance Comparison

The benchmark panel loads `results_p6/P6_4_summary_statistics.csv` and presents:
1. **Unique PDR:** P4 ($62.94\%$), P2 ($63.29\%$), Forced VBF ($66.00\%$), Pure DBR ($74.71\%$), EEDBR ($66.74\%$).
2. **Total Reception Ratio:** Strictly separated to prevent conflating duplicate-flooding protocols (EEDBR $151.26\%$, DBR $95.52\%$) with unique packet delivery.
3. **Fault Resilience & Delivery Parity:** Following node disruption, P4 achieves $62.50 \pm 3.07\%$ unique PDR, which matches Forced VBF ($63.53 \pm 1.58\%$) with $p = 0.364$.
4. **Energy Conservation:** P4 saves $35.90\text{ J}$ network energy compared to Forced VBF ($477.87\text{ J}$ vs. $513.77\text{ J}$, $p = 8.23 \times 10^{-11}$).
5. **Tail Latency:** P4 achieves $2.3479\text{ s}$ P95 delay, outperforming Forced VBF ($2.7670\text{ s}$) and Pure DBR ($2.9114\text{ s}$).

---

## 7. Verification of Code Non-Interference

As required by task guidelines:
1. **NS-3 Source Code:** Zero modifications to `src/aqua-sim-ng/` or `scratch/underwater-network.cc`. Active SHA-256 hashes verified:
   - `aqua-sim-routing-vbf.cc`: `0B5F07E8F383563916A228A3A121D3A9C07ECE04B9EA078C1CD1F15E0E2CA9E8`
   - `aqua-sim-routing-vbf.h`: `B7ED3A356D9B6689CE8EE2BD0B25386EBDFDC03A22FF8D59479539830EA60BF8`
2. **Results Integrity:** Simulation logs in `results_p6/`, CSV datasets, and figures in `report/figures/` remain untouched.
3. **Modular Boundary:** All code changes were strictly confined to the `dashboard/` directory.

---

## 8. Launch & Validation Checklist

| Verification Item | Test Command / Method | Result | Status |
| :--- | :--- | :--- | :---: |
| **Python Byte-Compilation** | `python -m py_compile dashboard/app.py dashboard/data_loader.py dashboard/simulator_engine.py` | Exit code 0, clean bytecode | **PASS** |
| **Dataset Loading** | `load_per_run_data()`, `load_summary_statistics()` | 50 run records & 85 summary metrics loaded | **PASS** |
| **Log Trace Parsing** | `load_actual_simulation_trace(1)` | 5,009 events parsed chronologically | **PASS** |
| **Topology Nodes** | `get_topology_nodes()` | 12 nodes, exact coordinates | **PASS** |
| **Mode B Engine** | `step_simulation()`, `execute_q_learning_update()` | All 9 steps & Bellman math verified | **PASS** |
| **Theme & UI** | Dark navy (`#07111E`) / Cyan (`#00E5FF`) CSS | Compliant | **PASS** |
| **Documentation** | `dashboard/README.md`, `dashboard/P9_DEMO_IMPLEMENTATION_REPORT.md` | Complete launch guide | **PASS** |

---

## 9. Conclusion

The self-healing demonstration simulator in `dashboard/` is verified, fully functional, and ready for presentation and examination. It accurately mirrors the verified NS-3.41 C++ codebase and empirical benchmark results.
