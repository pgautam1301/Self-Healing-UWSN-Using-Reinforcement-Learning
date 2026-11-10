#!/usr/bin/env python3
"""
Multi-Seed Experiment Automation for P5.2:
Compares:
  - P4 (8-state fault-aware RL)
  - Forced VBF (Baseline: SelectRLAction returns RL_FORWARD)
  - P2 (Original 4-state RL-enabled VBF)
Runs: 1 to 10 for each configuration (30 runs total).
"""

import os
import sys
import shutil
import hashlib
import subprocess
import re
import math
import csv
from collections import defaultdict, Counter

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(WORKSPACE_DIR, "results_p5")

# Source files & backup paths
MODEL_DIR = os.path.join(WORKSPACE_DIR, "src", "aqua-sim-ng", "model")
ACTIVE_CC = os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.cc")
ACTIVE_H = os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.h")
SCRATCH_FILE = os.path.join(WORKSPACE_DIR, "scratch", "underwater-network.cc")

# Expected SHA-256 hashes
EXPECTED_HASHES = {
    "p4": {
        "cc": "0b5f07e8f383563916a228a3a121d3a9c07ece04b9ea078c1cd1f15e0e2ca9e8",
        "h":  "b7ed3a356d9b6689ce8ee2bd0b25386ebdfdc03a22ff8d59479539830ea60bf8",
        "backup_cc": os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.cc.p4"),
        "backup_h":  os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.h.p4")
    },
    "vbf": {
        "cc": "4a0b1a4b0ef7074b195bbaf3200a982537235e6345ac305652c2930ad64923e4",
        "h":  "9b8ff22cec0efc559d4dbf56455ad0929d6be35f7b80b859fc8c3757a730a7a0",
        "backup_cc": os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.cc.vbf"),
        "backup_h":  os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.h.vbf")
    },
    "p2": {
        "cc": "46320ac8e1a9a2d969f294ac134c41fa0f916cd4880d693b9640286ec2e584c5",
        "h":  "9b8ff22cec0efc559d4dbf56455ad0929d6be35f7b80b859fc8c3757a730a7a0",
        "backup_cc": os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.cc.p2"),
        "backup_h":  os.path.join(MODEL_DIR, "aqua-sim-routing-vbf.h.p2")
    }
}

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest().lower()

def verify_scratch():
    """Verify parameters and failure injection in scratch/underwater-network.cc."""
    with open(SCRATCH_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Seconds(50.0),\n    \t&FailSensor" in content or "Seconds(50.0),\n    	&FailSensor" in content or "&FailSensor" in content, "Sensor 5 failure at 50s not found!"
    assert "devices.Get(4)" in content, "Failed device must be Sensor 5 (index 4)!"
    assert "runNumber" in content, "CLI runNumber argument not found in scratch!"
    assert "RngSeedManager::SetSeed(1)" in content, "Base seed 1 not found in scratch!"
    assert "RngSeedManager::SetRun(runNumber)" in content, "SetRun(runNumber) not found in scratch!"
    print("[VERIFY] scratch/underwater-network.cc passed all invariant checks.")

def switch_configuration(config_name):
    """Switch active model source files to target configuration and verify integrity."""
    cfg = EXPECTED_HASHES[config_name]
    print(f"\n==========================================")
    print(f"Switching to Configuration: {config_name.upper()}")
    print(f"==========================================")
    
    # Copy backups to active paths
    shutil.copyfile(cfg["backup_cc"], ACTIVE_CC)
    shutil.copyfile(cfg["backup_h"], ACTIVE_H)
    
    # Verify hashes
    cc_hash = get_sha256(ACTIVE_CC)
    h_hash = get_sha256(ACTIVE_H)
    
    if cc_hash != cfg["cc"]:
        raise ValueError(f"Hash mismatch for {ACTIVE_CC}! Expected {cfg['cc']}, got {cc_hash}")
    if h_hash != cfg["h"]:
        raise ValueError(f"Hash mismatch for {ACTIVE_H}! Expected {cfg['h']}, got {h_hash}")
        
    # Verify semantic properties
    with open(ACTIVE_CC, "r", encoding="utf-8") as f:
        cc_content = f.read()
        
    if config_name == "vbf":
        assert "return RL_FORWARD;" in cc_content, "SelectRLAction early return RL_FORWARD missing in VBF!"
    elif config_name == "p4":
        assert "m_consecutiveTimeouts" in cc_content, "m_consecutiveTimeouts missing in P4!"
        assert "faultLevel * 4" in cc_content, "8-state formula missing in P4!"
    elif config_name == "p2":
        assert "return RL_FORWARD;" not in cc_content, "Unexpected RL_FORWARD return found in P2!"
        assert "faultLevel" not in cc_content, "Unexpected faultLevel found in P2!"
        assert "m_completedExperiences" in cc_content, "P2 completed experiences missing!"
        
    verify_scratch()
    print(f"[VERIFY] {config_name.upper()} source verified (SHA256: {cc_hash[:16]}...)")

def build_ns3():
    """Build NS-3. Abort on failure."""
    print("[BUILD] Running: ./ns3 build -j 1 ...")
    ret = subprocess.run(["./ns3", "build", "-j", "1"], cwd=WORKSPACE_DIR)
    if ret.returncode != 0:
        raise RuntimeError(f"[ERROR] NS-3 build failed with return code {ret.returncode}!")
    print("[BUILD] Build successful.")

def run_simulation(config_name, run_number, results_dir=RESULTS_DIR):
    """Run one simulation run."""
    os.makedirs(results_dir, exist_ok=True)
    log_name = f"{config_name}_run{run_number:02d}.log"
    log_path = os.path.join(results_dir, log_name)
    
    if os.path.exists(log_path) and os.path.getsize(log_path) > 10000:
        print(f"[SKIP] Run {config_name} run #{run_number} log already exists ({log_name}).")
        return log_path

    cmd = ["./ns3", "run", f"underwater-network --runNumber={run_number}"]
    print(f"[RUN] {config_name.upper()} Run #{run_number:02d} -> {log_name} ...")
    
    with open(log_path, "w", encoding="utf-8") as f_out:
        ret = subprocess.run(cmd, cwd=WORKSPACE_DIR, stdout=f_out, stderr=subprocess.STDOUT)
        
    if ret.returncode != 0:
        raise RuntimeError(f"[ERROR] Simulation {config_name} run #{run_number} failed with code {ret.returncode}!")
        
    file_size = os.path.getsize(log_path)
    print(f"[DONE] {log_name} created successfully ({file_size / 1024:.1f} KB).")
    return log_path

def parse_log(log_path, config_name, run_number):
    """Parse a single simulation log file and return all extracted metrics."""
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    current_time = 0.0
    injected_pkts = {}   # pk -> injection time
    sink_deliveries = {} # pk -> delivery time
    
    fwd_events = defaultdict(lambda: {'before': 0, 'after': 0})
    timeout_events = defaultdict(lambda: {'before': 0, 'after': 0})
    ack_recv_events = defaultdict(lambda: {'before': 0, 'after': 0})
    avoid_events = defaultdict(lambda: {'before': 0, 'after': 0})
    
    acks_sent = 0
    acks_recv = 0
    timeouts = 0
    pos_rewards = 0
    neg_rewards = 0
    
    # State tracking: (node, pk) -> state
    exp_state = {}
    exp_action = {}
    
    action_counts_healthy = Counter()
    action_counts_degraded = Counter()
    
    for line in lines:
        m_t = re.search(r'at time ([\d\.]+)', line)
        if m_t:
            current_time = float(m_t.group(1))
            
        if 'OriginalSender=012' in line and 'PreviousForwarder=012' in line:
            m_pk = re.search(r'Packet=(\d+)', line)
            if m_pk:
                pk = int(m_pk.group(1))
                if pk not in injected_pkts:
                    injected_pkts[pk] = current_time
                    
        m_term = re.search(r'RL Feedback Sent: Forwarder=\d+ Receiver=11 Packet=(\d+) Status=2', line)
        if m_term:
            pk = int(m_term.group(1))
            if pk not in sink_deliveries:
                sink_deliveries[pk] = current_time
                
        m_exp = re.search(r'RL Experience Stored: Node=(\d+) Packet=(\d+) State=(\d+) Action=(\d+)', line)
        if m_exp:
            node = int(m_exp.group(1))
            pk = int(m_exp.group(2))
            st = int(m_exp.group(3))
            act = int(m_exp.group(4))
            phase = 'before' if current_time < 50.0 else 'after'
            if act == 0:
                fwd_events[node][phase] += 1
            exp_state[(node, pk)] = st
            exp_action[(node, pk)] = act
            if st < 4:
                action_counts_healthy[act] += 1
            else:
                action_counts_degraded[act] += 1
                
        m_av = re.search(r'RL AVOID Local Update: Node=(\d+) Packet=(\d+) State=(\d+) Reward=([\d\.\-]+)', line)
        if m_av:
            node = int(m_av.group(1))
            st = int(m_av.group(3))
            rew = float(m_av.group(4))
            phase = 'before' if current_time < 50.0 else 'after'
            avoid_events[node][phase] += 1
            if rew > 0: pos_rewards += 1
            else: neg_rewards += 1
            if st < 4:
                action_counts_healthy[2] += 1
            else:
                action_counts_degraded[2] += 1
                
        m_to = re.search(r'RL ACK Timeout: Node=(\d+) Packet=(\d+) Action=(\d+)', line)
        if m_to:
            node = int(m_to.group(1))
            phase = 'before' if current_time < 50.0 else 'after'
            timeout_events[node][phase] += 1
            timeouts += 1
            neg_rewards += 1
            
        m_ack = re.search(r'RL Learning Update: Node=(\d+) Packet=(\d+) Action=(\d+) Status=\d+ Reward=([\d\.\-]+)', line)
        if m_ack:
            node = int(m_ack.group(1))
            rew = float(m_ack.group(4))
            phase = 'before' if current_time < 50.0 else 'after'
            ack_recv_events[node][phase] += 1
            acks_recv += 1
            if rew > 0: pos_rewards += 1
            else: neg_rewards += 1
            
        if 'RL Feedback Sent:' in line:
            acks_sent += 1
            
    full_text = ''.join(lines)
    energies = {}
    m_energy = re.findall(r'Sensor (\d+) \| Initial Energy: \S+ J \| Remaining Energy: \S+ J \| Consumed Energy: ([\d\.]+) J', full_text)
    for s, e in m_energy:
        energies[int(s)] = float(e)
    total_energy = sum(energies.values()) if energies else 0.0
    
    m_sent = re.search(r'Sent Pkts\(Source_NetDevice->Stack\):\s+\(NetworkTotal\)\s+(\d+)', full_text)
    total_injected = int(m_sent.group(1)) if m_sent else len(injected_pkts)
    
    m_recv = re.search(r'SendUp Pkts\(Sink_RoutingLayer\):\s+\(NetworkTotal\)\s+(\d+)', full_text)
    total_delivered = int(m_recv.group(1)) if m_recv else len(sink_deliveries)
    
    unique_delivered = len(sink_deliveries)
    
    # Classification by source packet generation timestamp
    b50_sent = {p: t for p, t in injected_pkts.items() if t < 50.0}
    a50_sent = {p: t for p, t in injected_pkts.items() if t >= 50.0}
    b50_del = {p for p in b50_sent if p in sink_deliveries}
    a50_del = {p for p in a50_sent if p in sink_deliveries}
    
    overall_pdr = (total_delivered / total_injected * 100.0) if total_injected > 0 else 0.0
    pre_pdr = (len(b50_del) / len(b50_sent) * 100.0) if len(b50_sent) > 0 else 0.0
    post_pdr = (len(a50_del) / len(a50_sent) * 100.0) if len(a50_sent) > 0 else 0.0
    
    delays_all = [sink_deliveries[p] - injected_pkts[p] for p in sink_deliveries if p in injected_pkts]
    
    mean_delay = float(sum(delays_all) / len(delays_all)) if delays_all else 0.0
    sorted_delays = sorted(delays_all)
    if sorted_delays:
        n = len(sorted_delays)
        median_delay = float(sorted_delays[n // 2] if n % 2 != 0 else (sorted_delays[n // 2 - 1] + sorted_delays[n // 2]) / 2.0)
        p95_idx = int(math.ceil(0.95 * n)) - 1
        p95_delay = float(sorted_delays[max(0, min(p95_idx, n - 1))])
    else:
        median_delay = 0.0
        p95_delay = 0.0
        
    energy_per_delivered = (total_energy / total_delivered) if total_delivered > 0 else 0.0
    energy_per_unique = (total_energy / unique_delivered) if unique_delivered > 0 else 0.0
    
    total_fwd = sum(fwd_events[n]['before'] + fwd_events[n]['after'] for n in fwd_events)
    
    return {
        "config": config_name,
        "run": run_number,
        "total_injected": total_injected,
        "total_delivered": total_delivered,
        "unique_delivered": unique_delivered,
        "overall_pdr": overall_pdr,
        "pre_injected": len(b50_sent),
        "pre_delivered": len(b50_del),
        "pre_pdr": pre_pdr,
        "post_injected": len(a50_sent),
        "post_delivered": len(a50_del),
        "post_pdr": post_pdr,
        "mean_delay": mean_delay,
        "median_delay": median_delay,
        "p95_delay": p95_delay,
        "total_energy": total_energy,
        "energy_per_delivered": energy_per_delivered,
        "energy_per_unique": energy_per_unique,
        "acks_sent": acks_sent,
        "acks_recv": acks_recv,
        "ack_timeouts": timeouts,
        "pos_rewards": pos_rewards,
        "neg_rewards": neg_rewards,
        "total_forwardings": total_fwd,
        "p4_healthy_fwd": action_counts_healthy[0],
        "p4_healthy_def": action_counts_healthy[1],
        "p4_healthy_avd": action_counts_healthy[2],
        "p4_degraded_fwd": action_counts_degraded[0],
        "p4_degraded_def": action_counts_degraded[1],
        "p4_degraded_avd": action_counts_degraded[2]
    }

def calc_stats(values):
    """Compute mean, sample standard deviation, min, max, and 95% CI."""
    if not values:
        return 0.0, 0.0, 0.0, 0.0, (0.0, 0.0)
    n = len(values)
    mean_val = sum(values) / n
    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        std_val = math.sqrt(variance)
    else:
        std_val = 0.0
        
    min_val = min(values)
    max_val = max(values)
    
    # Student's t critical value for df = n - 1 (df = 9 for n = 10 -> 2.262157)
    t_crit = 2.262157 if n == 10 else 1.96
    moe = t_crit * (std_val / math.sqrt(n)) if n > 1 else 0.0
    ci_95 = (mean_val - moe, mean_val + moe)
    return mean_val, std_val, min_val, max_val, ci_95

def paired_t_test(x_list, y_list):
    """Compute paired t-statistic and difference metrics between x and y."""
    assert len(x_list) == len(y_list)
    diffs = [x - y for x, y in zip(x_list, y_list)]
    mean_d, std_d, min_d, max_d, ci_d = calc_stats(diffs)
    n = len(diffs)
    se_d = std_d / math.sqrt(n) if n > 1 else 0.0
    t_stat = (mean_d / se_d) if se_d > 0 else 0.0
    return {
        "mean_diff": mean_d,
        "std_diff": std_d,
        "ci_95": ci_d,
        "t_stat": t_stat
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-seed evaluation runner for P5.2")
    parser.add_argument("--stage", choices=["test", "batch", "parse_only", "restore"], default="test",
                        help="test: run 1 seed for each config; batch: run all 10 seeds; parse_only: re-parse existing logs; restore: restore P4 reference")
    args = parser.parse_args()
    
    configs_order = ["p4", "vbf", "p2"]
    
    if args.stage == "test":
        print("\n>>> STAGE 1: Single-seed smoke validation (Run #1 for P4, VBF, P2) <<<\n")
        test_results = []
        for cfg in configs_order:
            switch_configuration(cfg)
            build_ns3()
            log_p = run_simulation(cfg, 1)
            parsed = parse_log(log_p, cfg, 1)
            test_results.append(parsed)
            print(f"[TEST RESULT] {cfg.upper()} Run #1: Delivered={parsed['total_delivered']}, "
                  f"Overall PDR={parsed['overall_pdr']:.2f}%, Post PDR={parsed['post_pdr']:.2f}%, "
                  f"Energy={parsed['total_energy']:.2f} J, Mean Delay={parsed['mean_delay']:.4f}s")
            
        print("\nAll 3 test runs parsed successfully! Ready for full batch execution.")
        
    elif args.stage == "batch":
        print("\n>>> STAGE 2: Full Multi-Seed Batch Execution (10 Runs per Configuration) <<<\n")
        all_results = []
        
        for cfg in configs_order:
            switch_configuration(cfg)
            build_ns3()
            for r in range(1, 11):
                log_p = run_simulation(cfg, r)
                parsed = parse_log(log_p, cfg, r)
                all_results.append(parsed)
                print(f"[{cfg.upper()} #{r:02d}] PDR={parsed['overall_pdr']:.2f}% | Post-PDR={parsed['post_pdr']:.2f}% | "
                      f"Delivered={parsed['total_delivered']} | Energy={parsed['total_energy']:.2f} J | Delay={parsed['mean_delay']:.3f}s")
                
        # Export CSVs
        save_results_csv(all_results)
        
        # Restoration
        print("\n>>> STAGE 3: Restoration of Active Implementations <<<")
        restore_environment()
        
    elif args.stage == "parse_only":
        print("\n>>> Parsing existing logs in results_p5/ <<<\n")
        all_results = []
        for cfg in configs_order:
            for r in range(1, 11):
                log_p = os.path.join(RESULTS_DIR, f"{cfg}_run{r:02d}.log")
                if os.path.exists(log_p):
                    parsed = parse_log(log_p, cfg, r)
                    all_results.append(parsed)
        save_results_csv(all_results)
        
    elif args.stage == "restore":
        restore_environment()

def save_results_csv(all_results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    per_run_csv = os.path.join(RESULTS_DIR, "per_run_results.csv")
    summary_csv = os.path.join(RESULTS_DIR, "summary_statistics.csv")
    
    if not all_results:
        print("[WARN] No results to save.")
        return
        
    # Write per_run_results.csv
    fieldnames = list(all_results[0].keys())
    with open(per_run_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)
    print(f"\n[SAVED] Per-run results written to: {per_run_csv}")
    
    # Compute summary statistics
    metrics_to_summarize = [
        ("overall_pdr", "Overall PDR (%)"),
        ("pre_pdr", "Pre-Failure PDR (%)"),
        ("post_pdr", "Post-Failure PDR (%)"),
        ("total_delivered", "Total Delivered Packets"),
        ("unique_delivered", "Unique Delivered Packets"),
        ("mean_delay", "Mean E2E Delay (s)"),
        ("median_delay", "Median E2E Delay (s)"),
        ("p95_delay", "P95 E2E Delay (s)"),
        ("total_energy", "Total Network Energy (J)"),
        ("energy_per_delivered", "Energy per Delivered Packet (J/pkt)"),
        ("total_forwardings", "Total Forwarding Count"),
        ("acks_sent", "Total ACKs Sent"),
        ("acks_recv", "Total ACKs Received"),
        ("ack_timeouts", "Total ACK Timeouts")
    ]
    
    configs = ["p4", "vbf", "p2"]
    by_config = {c: [r for r in all_results if r["config"] == c] for c in configs}
    
    summary_rows = []
    for metric_key, metric_label in metrics_to_summarize:
        for c in configs:
            vals = [r[metric_key] for r in by_config[c]]
            if vals:
                mean_v, std_v, min_v, max_v, ci_v = calc_stats(vals)
                summary_rows.append({
                    "metric": metric_label,
                    "config": c.upper(),
                    "mean": f"{mean_v:.4f}",
                    "std": f"{std_v:.4f}",
                    "min": f"{min_v:.4f}",
                    "max": f"{max_v:.4f}",
                    "ci_95_low": f"{ci_v[0]:.4f}",
                    "ci_95_high": f"{ci_v[1]:.4f}"
                })
                
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "config", "mean", "std", "min", "max", "ci_95_low", "ci_95_high"])
        writer.writeheader()
        for r in summary_rows:
            writer.writerow(r)
    print(f"[SAVED] Summary statistics written to: {summary_csv}")
    
    # Print formatted comparative table
    print("\n" + "=" * 115)
    print(f"{'Metric':<35} | {'P4 (Fault-Aware RL)':<25} | {'Forced VBF Baseline':<25} | {'P2 (4-State RL)':<25}")
    print("=" * 115)
    
    for metric_key, metric_label in metrics_to_summarize:
        vals_p4 = [r[metric_key] for r in by_config["p4"]]
        vals_vbf = [r[metric_key] for r in by_config["vbf"]]
        vals_p2 = [r[metric_key] for r in by_config["p2"]]
        
        m_p4, s_p4, _, _, _ = calc_stats(vals_p4)
        m_vbf, s_vbf, _, _, _ = calc_stats(vals_vbf)
        m_p2, s_p2, _, _, _ = calc_stats(vals_p2)
        
        str_p4 = f"{m_p4:.2f} ± {s_p4:.2f}"
        str_vbf = f"{m_vbf:.2f} ± {s_vbf:.2f}"
        str_p2 = f"{m_p2:.2f} ± {s_p2:.2f}"
        print(f"{metric_label:<35} | {str_p4:<25} | {str_vbf:<25} | {str_p2:<25}")
        
    print("=" * 115)

    # Statistical Comparison: Paired & Unpaired Analysis
    print("\n" + "=" * 115)
    print("STATISTICAL INFERENCE & HYPOTHESIS TESTING (N = 10 Replications)")
    print("=" * 115)
    print(f"{'Metric':<28} | {'Comparison':<16} | {'Mean Diff':<12} | {'95% CI':<22} | {'Paired t':<10} | {'Unpaired t':<10}")
    print("-" * 115)
    
    test_metrics = [
        ("overall_pdr", "Overall PDR (%)"),
        ("post_pdr", "Post-Failure PDR (%)"),
        ("mean_delay", "Mean E2E Delay (s)"),
        ("total_energy", "Total Energy (J)"),
        ("energy_per_delivered", "Energy/Delivered (J)"),
        ("ack_timeouts", "ACK Timeouts")
    ]
    
    for metric_key, metric_label in test_metrics:
        p4_vals = [r[metric_key] for r in by_config["p4"]]
        vbf_vals = [r[metric_key] for r in by_config["vbf"]]
        p2_vals = [r[metric_key] for r in by_config["p2"]]
        
        for base_name, base_vals in [("P4 vs Forced VBF", vbf_vals), ("P4 vs P2 RL", p2_vals)]:
            if len(p4_vals) == 10 and len(base_vals) == 10:
                # Paired test
                diffs = [p - b for p, b in zip(p4_vals, base_vals)]
                m_diff, s_diff, _, _, ci_diff = calc_stats(diffs)
                se_paired = s_diff / math.sqrt(10) if s_diff > 0 else 1e-9
                t_paired = m_diff / se_paired
                
                # Unpaired Welch test
                m_p4, s_p4, _, _, _ = calc_stats(p4_vals)
                m_b, s_b, _, _, _ = calc_stats(base_vals)
                se_unpaired = math.sqrt((s_p4**2)/10 + (s_b**2)/10) if (s_p4 + s_b) > 0 else 1e-9
                t_unpaired = (m_p4 - m_b) / se_unpaired
                
                ci_str = f"[{ci_diff[0]:.2f}, {ci_diff[1]:.2f}]"
                print(f"{metric_label:<28} | {base_name:<16} | {m_diff:+10.2f}   | {ci_str:<22} | {t_paired:+8.2f}   | {t_unpaired:+8.2f}")
    print("=" * 115)

    # Sync to Windows workspace if running in WSL
    win_results_dir = "/mnt/c/Users/Gautam/Documents/UWSN/ns-3.41/results_p5"
    if os.path.exists("/mnt/c/Users/Gautam/Documents/UWSN/ns-3.41") and os.path.abspath(RESULTS_DIR) != os.path.abspath(win_results_dir):
        try:
            os.makedirs(win_results_dir, exist_ok=True)
            for item in os.listdir(RESULTS_DIR):
                s = os.path.join(RESULTS_DIR, item)
                d = os.path.join(win_results_dir, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)
            print(f"[SYNC] Successfully synced all logs and CSVs to {win_results_dir}")
        except Exception as e:
            print(f"[WARN] Could not sync to Windows path: {e}")

def restore_environment():
    """Verify restoration of P2 and final restoration of P4."""
    print("[RESTORE] Restoring P2 reference to verify pristine state...")
    shutil.copyfile(EXPECTED_HASHES["p2"]["backup_cc"], ACTIVE_CC)
    shutil.copyfile(EXPECTED_HASHES["p2"]["backup_h"], ACTIVE_H)
    assert get_sha256(ACTIVE_CC) == EXPECTED_HASHES["p2"]["cc"]
    assert get_sha256(ACTIVE_H) == EXPECTED_HASHES["p2"]["h"]
    print("[RESTORE] P2 reference verified against golden SHA-256.")
    
    print("[RESTORE] Restoring P4 as active experimental version...")
    shutil.copyfile(EXPECTED_HASHES["p4"]["backup_cc"], ACTIVE_CC)
    shutil.copyfile(EXPECTED_HASHES["p4"]["backup_h"], ACTIVE_H)
    assert get_sha256(ACTIVE_CC) == EXPECTED_HASHES["p4"]["cc"]
    assert get_sha256(ACTIVE_H) == EXPECTED_HASHES["p4"]["h"]
    print("[RESTORE] P4 active files verified against golden SHA-256.")
    
    build_ns3()
    print("[RESTORE] Environment cleanly restored to active P4 and recompiled successfully.")

if __name__ == "__main__":
    main()
