#!/bin/bash
set -e

BASE_DIR="/home/gautam/underwater-project/ns-allinone-3.41/ns-3.41"
OUT_DIR="/mnt/c/Users/Gautam/Documents/UWSN/ns-3.41/results_p6"
VBF_DIR="$BASE_DIR/src/aqua-sim-ng/model"

echo "=== Starting P6.4 50-Simulation Batch Evaluation ==="
date

cd "$BASE_DIR"

# 1. P4 (8-State Fault-Aware RL) - Active by default
echo "--- Step 1: Running P4 Fault-Aware RL (Runs 1-10) ---"
P4_HASH=$(sha256sum "$VBF_DIR/aqua-sim-routing-vbf.cc" | awk '{print $1}')
echo "P4 CC Hash: $P4_HASH"
if [ "$P4_HASH" != "0b5f07e8f383563916a228a3a121d3a9c07ece04b9ea078c1cd1f15e0e2ca9e8" ]; then
    echo "ERROR: P4 hash mismatch!"
    exit 1
fi

for r in $(seq -w 1 10); do
    run_num=$((10#$r))
    echo "Running P4 run $r ($run_num/10)..."
    ./ns3 run "underwater-network --routing=VBF --runNumber=$run_num" > "$OUT_DIR/p4_run${r}.log" 2>&1
done
echo "P4 completed."

# 2. Pure DBR (Runs 1-10)
echo "--- Step 2: Running Pure DBR (Runs 1-10) ---"
for r in $(seq -w 1 10); do
    run_num=$((10#$r))
    echo "Running DBR run $r ($run_num/10)..."
    ./ns3 run "underwater-network --routing=DBR --runNumber=$run_num" > "$OUT_DIR/dbr_run${r}.log" 2>&1
done
echo "DBR completed."

# 3. EEDBR (Runs 1-10)
echo "--- Step 3: Running EEDBR (Runs 1-10) ---"
for r in $(seq -w 1 10); do
    run_num=$((10#$r))
    echo "Running EEDBR run $r ($run_num/10)..."
    ./ns3 run "underwater-network --routing=EEDBR --runNumber=$run_num" > "$OUT_DIR/eedbr_run${r}.log" 2>&1
done
echo "EEDBR completed."

# 4. P2 Original RL (Runs 1-10)
echo "--- Step 4: Switching to P2 Original RL ---"
cp "$VBF_DIR/aqua-sim-routing-vbf.cc.p2" "$VBF_DIR/aqua-sim-routing-vbf.cc"
cp "$VBF_DIR/aqua-sim-routing-vbf.h.p2" "$VBF_DIR/aqua-sim-routing-vbf.h"
P2_HASH=$(sha256sum "$VBF_DIR/aqua-sim-routing-vbf.cc" | awk '{print $1}')
echo "P2 CC Hash: $P2_HASH"
if [ "$P2_HASH" != "46320ac8e1a9a2d969f294ac134c41fa0f916cd4880d693b9640286ec2e584c5" ]; then
    echo "ERROR: P2 hash mismatch!"
    exit 1
fi
./ns3 build -j 1

echo "--- Running P2 Original RL (Runs 1-10) ---"
for r in $(seq -w 1 10); do
    run_num=$((10#$r))
    echo "Running P2 run $r ($run_num/10)..."
    ./ns3 run "underwater-network --routing=VBF --runNumber=$run_num" > "$OUT_DIR/p2_run${r}.log" 2>&1
done
echo "P2 completed."

# 5. Forced-Forward VBF (Runs 1-10)
echo "--- Step 5: Switching to Forced-Forward VBF ---"
cp "$VBF_DIR/aqua-sim-routing-vbf.cc.vbf" "$VBF_DIR/aqua-sim-routing-vbf.cc"
cp "$VBF_DIR/aqua-sim-routing-vbf.h.vbf" "$VBF_DIR/aqua-sim-routing-vbf.h"
VBF_HASH=$(sha256sum "$VBF_DIR/aqua-sim-routing-vbf.cc" | awk '{print $1}')
echo "Forced VBF CC Hash: $VBF_HASH"
if [ "$VBF_HASH" != "4a0b1a4b0ef7074b195bbaf3200a982537235e6345ac305652c2930ad64923e4" ]; then
    echo "ERROR: Forced VBF hash mismatch!"
    exit 1
fi
./ns3 build -j 1

echo "--- Running Forced-Forward VBF (Runs 1-10) ---"
for r in $(seq -w 1 10); do
    run_num=$((10#$r))
    echo "Running Forced VBF run $r ($run_num/10)..."
    ./ns3 run "underwater-network --routing=VBF --runNumber=$run_num" > "$OUT_DIR/vbf_run${r}.log" 2>&1
done
echo "Forced VBF completed."

# 6. Restore P4 Fault-Aware RL and Verify Hashes
echo "--- Step 6: Restoring P4 Fault-Aware RL ---"
cp "$VBF_DIR/aqua-sim-routing-vbf.cc.p4" "$VBF_DIR/aqua-sim-routing-vbf.cc"
cp "$VBF_DIR/aqua-sim-routing-vbf.h.p4" "$VBF_DIR/aqua-sim-routing-vbf.h"
RESTORED_P4_HASH=$(sha256sum "$VBF_DIR/aqua-sim-routing-vbf.cc" | awk '{print $1}')
echo "Restored P4 CC Hash: $RESTORED_P4_HASH"
if [ "$RESTORED_P4_HASH" != "0b5f07e8f383563916a228a3a121d3a9c07ece04b9ea078c1cd1f15e0e2ca9e8" ]; then
    echo "ERROR: Restored P4 hash mismatch!"
    exit 1
fi
./ns3 build -j 1

echo "=== All 50 Simulations Completed Successfully! ==="
date
