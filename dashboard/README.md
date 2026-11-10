# Self-Healing UWSN Interactive Demonstration Simulator & Analytics Dashboard

**Project Title:** Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning  
**Simulation Framework:** Network Simulator 3 (NS-3.41) + Aqua-Sim Next Generation (Aqua-Sim NG)  
**Implementation Architecture:** P4 Fault-Aware 8-State Q-Learning VBF Routing  
**Evaluation Scope:** 50 multi-seed simulations across 5 routing protocols with scheduled node disruption  

---

## 1. Overview

This interactive Streamlit application provides an executive 3D demonstration simulator and analytics control deck for our B.Tech final-year minor project. It is styled with an executive pure black / charcoal and lavender aesthetic inspired by modern robotics and subsea control centers.

### Key Capabilities:
- **Executive 3D Overview:** WebGL Three.js interactive 3D underwater array with orbit camera controls (rotate, zoom, pan), marine particulate effect, progressive link drawing, traveling packet beacons, and Sensor 5 failure simulation with green bypass recovery.
- **Actual NS-3 Results Replay:** Replays real timestamp-ordered packet events from verified NS-3.41 simulation logs (`results_p6/p4_run01.log` through `run10.log`), including packet injection, intermediate routing decisions, Layer-3 reverse ACKs, unacknowledged timeouts, and the scheduled Sensor 5 failure at $t = 50.0\text{ s}$. Zero values are fabricated.
- **Interactive Step-by-Step Demonstration:** An educational step-by-step simulator walking through the 9-step failure, timeout detection, Bellman Q-table update, and spatial candidate bypass sequence with live mathematical breakdowns.
- **3D Network Builder:** Visual builder workspace allowing node repositioning, manual and automatic link connection, and JSON topology serialization.
- **Multi-Protocol Performance Benchmark:** Full comparative evaluation across five protocols (`p4`, `p2`, `vbf`, `dbr`, `eedbr`) using authoritative datasets (`P6_4_summary_statistics.csv` and `P6_4_per_run_results.csv`).
- **3D Underwater Topology Visualizer:** Interactive 3D coordinate space rendering the 12-node network using the reflected coordinate system ($z_{\text{new}} = 100 - z_{\text{old}}$).
- **RL Mathematical Architecture Inspector:** Detailed breakdown of the 3-dimensional binary state space ($(faultLevel \times 4) + (energyLevel \times 2) + progressLevel$), verified reward equations, and node-level timeout tracking boundaries.

---

## 2. Directory Structure

```text
dashboard/
├── app.py                            # Main Streamlit simulator and control center application
├── threejs_component.py              # WebGL Three.js interactive 3D subsea viewport component
├── static/                           # Local offline libraries for Three.js & OrbitControls
│   ├── three.min.js
│   └── OrbitControls.js
├── network_builder.py                # AquaNet 3D Network Builder workspace component
├── network_models.py                 # Core topological data models, validation, and defaults
├── network_visualization.py         # Plotly 3D WebGL and 2D orthogonal projection canvases
├── config_manager.py                 # JSON topology serialization and configuration manager
├── data_loader.py                    # Telemetry ingestion, log parsing, schema validation, and topology
├── simulator_engine.py               # Mode B educational demonstration engine and Bellman calculator
├── user_configs/                     # Saved JSON network topologies and template libraries
│   ├── default_project_topology.json # Authoritative 12-node project topology
│   ├── sparse_linear_corridor.json   # 7-node minimal relay corridor
│   └── dense_redundant_cluster.json  # 14-node redundant spatial cluster
├── test_network_builder.py           # Comprehensive verification test suite (15 criteria)
├── test_redesign_pages.py            # Comprehensive verification test suite for all 7 views
├── requirements.txt                  # Python package dependencies
├── README.md                         # Comprehensive setup, launch, and user guide
├── UI_REDESIGN_REPORT.md             # Complete UI Redesign Documentation & Audit
└── P10_1_NETWORK_BUILDER_REPORT.md   # P10.1 Phase Completion and Delivery Report
```

---

## 3. Installation & Launch Guide

### Prerequisites
- Python 3.9+ (Python 3.11+ recommended)
- `pip` package manager

### Option A: Windows (PowerShell / Command Prompt)

1. Open PowerShell or Command Prompt.
2. Navigate to the `dashboard/` directory:
   ```powershell
   cd c:\Users\Gautam\Documents\UWSN\ns-3.41\dashboard
   ```
3. (Optional) Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
4. Install required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Launch the Streamlit application:
   ```powershell
   streamlit run app.py
   ```
6. The dashboard will launch in your default browser at `http://localhost:8501`.

### Option B: Linux / WSL Ubuntu

1. Open your terminal.
2. Navigate to the project directory:
   ```bash
   cd /mnt/c/Users/Gautam/Documents/UWSN/ns-3.41/dashboard
   ```
3. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
4. Run Streamlit:
   ```bash
   streamlit run app.py
   ```
5. Open `http://localhost:8501` in your browser.

---

## 4. Demonstration Modes

### Mode A: Actual NS-3 Results Replay
1. Select **Mode A: Actual NS-3 Results Replay** in the sidebar.
2. Select any multi-seed run (Runs 1 to 10).
3. Use the **Simulation Time Slider** to scrub across simulation time ($0.0\text{ s}$ to $100.0\text{ s}$).
4. Observe the physical network topology:
   - Seafloor Source (Node 12, Cyan Diamond) at $(50, 50, 0)\text{ m}$.
   - Surface Gateway Sink (Node 11, Green Square) at $(500, 500, 100)\text{ m}$.
   - Intermediate Sensors 1–10 (Blue Circles).
   - Sensor 5 (Node 5) transitions from active status to a pulsating Red 'X' with residual battery halted at $72.21\text{ J}$ when $t \ge 50.0\text{ s}$.
5. Filter by event type (`SOURCE_TX`, `RL_DECISION`, `RELAY_ACK`, `SINK_DELIVERY`, `ACK_TIMEOUT`, `SENSOR_FAILURE`).
6. Inspect the full chronological log table extracted from raw simulation traces.

### Mode B: Interactive Step-by-Step Simulator (Educational)
1. Select **Mode B: Interactive Step-by-Step Simulator** in the sidebar.
2. Use **Next Step** / **Previous Step** or the **Jump to Step** dropdown to advance through the 9-step failure & recovery sequence:
   - **Step 1:** Application Traffic Generation at Seafloor
   - **Step 2:** Normal Intermediate Forwarding via Sensor 4
   - **Step 3:** Downstream Reception & Reverse ACK Confirmation ($R = +7.80$)
   - **Step 4:** Scheduled Sensor 5 Disruption ($t = 50.0\text{ s}$)
   - **Step 5:** Subsequent Transmission & Missing Downstream ACK
   - **Step 6:** First ACK Timeout at Sensor 4 ($m\_consecutiveTimeouts = 1$, Penalty $R = -5.0$)
   - **Step 7:** Second Timeout & State Transition to Degraded State S7 ($m\_consecutiveTimeouts \ge 2$)
   - **Step 8:** Acoustic Deferral ($T_{\text{defer}} = 0.5\text{ s}$) & Spatial Candidate Bypass via Sensor 6
   - **Step 9:** Terminal Delivery to Surface Gateway & Parity Verified ($R = +20.0$)
3. View the **Real-Time Bellman Equation Calculation** box displaying exact mathematical substitutions of learning rate $\alpha = 0.1$, discount factor $\gamma = 0.9$, immediate reward $r$, and target values.
4. Inspect the dynamic **8×3 Q-Table Heatmap**.

### AquaNet 3D Underwater Network Builder
1. Select **AquaNet 3D Network Builder** in the sidebar.
2. **Visual 3D & 2D Canvas:**
   - Switch between **3D Volume**, **2D Depth Profile (X-Z)**, and **2D Top-Down Surface (X-Y)** projections.
   - Nodes are rendered with distinct semantic glyphs: Source (Cyan diamond `#45D6CB`), Sink (Green square `#10B981`), Sensors (Teal circles `#38BDF8`), and Failed Nodes (Red crosses `#EF4444`).
   - Acoustic links are color-coded: Aqua solid for reachable acoustic links ($d \le R_{\text{tx}}$) and Red dashed for overrange links.
   - Interactive transmission range wireframe rings are rendered for the selected active node.
3. **Node Management:**
   - Select any node to inspect/modify coordinates $(x, y, z)$, transmission range, initial energy, and status.
   - Designate active node as Source or Surface Sink.
   - Add new nodes with uniqueness validation or delete existing nodes.
4. **Link Management:**
   - Manually connect or disconnect node pairs.
   - Click **Auto-Connect Reachable** to link all pairs within acoustic transmission range.
   - Inspect link distances, transmission thresholds, and failure impact in the Links table.
5. **Configuration Management:**
   - Save custom network topologies to `dashboard/user_configs/<name>.json`.
   - Load saved configurations from disk.
   - Export topologies as standalone JSON files or import custom user JSON files.
   - Load pre-configured templates: **Default Project (12-Node)**, **Sparse Linear Corridor (7-Node)**, or **Dense Redundant Cluster (14-Node)**.

---

## 5. Verified Metric Semantics

- **Unique-Packet PDR:** Calculated strictly as unique packet UIDs received at the sink routing layer divided by total injected packets ($310$).
- **Total Reception Ratio:** Duplicate-inclusive sink receptions divided by injected packets. EEDBR ($151.26\%$) and Pure DBR ($95.52\%$) reflect multi-copy packet flooding, not superior unique telemetry delivery.
- **Latency:** Evaluated on unique packets at first arrival time ($t_{\text{first\_rx}} - t_{\text{tx}}$).
- **Energy Conservation:** P4 saves $35.90\text{ J}$ network energy compared to Forced VBF ($477.87\text{ J}$ vs. $513.77\text{ J}$, $p = 8.23 \times 10^{-11}$).
- **Post-Failure Delivery Parity:** Following Sensor 5 disruption, P4 achieves $62.50\%$ unique PDR, matching Forced VBF ($63.53\%$, $p = 0.364$).
