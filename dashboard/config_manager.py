"""
config_manager.py - File I/O and Configuration Management for AquaNet Network Builder.
Project: Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning
Module: Configuration Storage Layer
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from network_models import NetworkTopology, Node, get_default_project_topology


def get_configs_dir() -> str:
    """Returns absolute path to user_configs directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    configs_dir = os.path.join(base_dir, "user_configs")
    os.makedirs(configs_dir, exist_ok=True)
    return configs_dir


def sanitize_filename(name: str) -> str:
    """Sanitizes configuration name for file system storage."""
    s = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name.strip())
    if not s.endswith(".json"):
        s += ".json"
    return s


def save_configuration(topology: NetworkTopology, config_name: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates and saves network topology as JSON in dashboard/user_configs/.
    Never overwrites experimental datasets.
    """
    is_valid, issues = topology.validate()
    if not is_valid:
        return False, f"Validation Failed: {'; '.join(issues)}", None

    configs_dir = get_configs_dir()
    clean_name = sanitize_filename(config_name)
    filepath = os.path.join(configs_dir, clean_name)

    data = topology.to_dict()
    data["metadata"] = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node_count": len(topology.nodes),
        "link_count": len(topology.links),
        "source_id": topology.get_source_node().id if topology.get_source_node() else None,
        "sink_id": topology.get_sink_node().id if topology.get_sink_node() else None
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True, f"Configuration successfully saved to '{clean_name}'.", filepath
    except Exception as e:
        return False, f"Error writing file: {str(e)}", None


def load_configuration(filename_or_path: str) -> Tuple[Optional[NetworkTopology], str]:
    """Loads network topology from JSON."""
    configs_dir = get_configs_dir()
    if not os.path.isabs(filename_or_path):
        filepath = os.path.join(configs_dir, filename_or_path)
    else:
        filepath = filename_or_path

    if not os.path.exists(filepath):
        return None, f"Configuration file not found: {filepath}"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        topo = NetworkTopology.from_dict(data)
        return topo, f"Loaded configuration '{topo.name}' ({len(topo.nodes)} nodes, {len(topo.links)} links)."
    except Exception as e:
        return None, f"Error parsing JSON configuration: {str(e)}"


def list_saved_configurations() -> List[Dict[str, Any]]:
    """Lists all saved configuration JSON files with metadata."""
    configs_dir = get_configs_dir()
    items = []

    for fname in sorted(os.listdir(configs_dir)):
        if fname.endswith(".json"):
            fp = os.path.join(configs_dir, fname)
            try:
                stat = os.stat(fp)
                with open(fp, "r", encoding="utf-8") as f:
                    d = json.load(f)
                meta = d.get("metadata", {})
                items.append({
                    "filename": fname,
                    "filepath": fp,
                    "name": d.get("name", fname),
                    "node_count": meta.get("node_count", len(d.get("nodes", []))),
                    "link_count": meta.get("link_count", len(d.get("links", []))),
                    "saved_at": meta.get("saved_at", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")),
                    "description": d.get("description", "")
                })
            except Exception:
                items.append({
                    "filename": fname,
                    "filepath": fp,
                    "name": fname,
                    "node_count": 0,
                    "link_count": 0,
                    "saved_at": "Unknown",
                    "description": "Corrupted or non-standard JSON"
                })

    return items


def ensure_sample_configs_exist():
    """Generates standard starter topologies if they do not exist."""
    configs_dir = get_configs_dir()

    # 1. Authoritative Default Reflected Topology
    default_path = os.path.join(configs_dir, "default_project_topology.json")
    if not os.path.exists(default_path):
        def_topo = get_default_project_topology()
        save_configuration(def_topo, "default_project_topology.json")

    # 2. Sparse Linear Acoustic Corridor (7 nodes)
    sparse_path = os.path.join(configs_dir, "sparse_linear_corridor.json")
    if not os.path.exists(sparse_path):
        s_topo = NetworkTopology(
            name="Sparse Linear Corridor (7 Nodes)",
            description="Minimal relay chain testing multi-hop latency and isolated void failure."
        )
        s_topo.add_node(Node(1, "Seafloor Source", "source", 50, 50, 0, 100, 200))
        for i in range(1, 6):
            s_topo.add_node(Node(i+1, f"Relay {i}", "sensor", 50 + i*60, 50 + i*60, i*16, 100, 200))
        s_topo.add_node(Node(7, "Surface Sink", "sink", 410, 410, 100, 100, 200))
        s_topo.auto_connect_reachable()
        save_configuration(s_topo, "sparse_linear_corridor.json")

    # 3. Dense Redundant Cluster (14 nodes)
    dense_path = os.path.join(configs_dir, "dense_redundant_cluster.json")
    if not os.path.exists(dense_path):
        d_topo = NetworkTopology(
            name="Dense Redundant Cluster (14 Nodes)",
            description="Highly meshed deployment testing spatial candidate bypass and duplicate suppression."
        )
        d_topo.add_node(Node(14, "Deep Source", "source", 50, 50, 0, 100, 250))
        nid = 1
        for z in [20, 45, 70]:
            for offset_x in [-60, 0, 60]:
                for offset_y in [-60, 60]:
                    if nid <= 12:
                        d_topo.add_node(Node(nid, f"Cluster Node {nid}", "sensor", 250 + offset_x, 250 + offset_y, z, 100, 250))
                        nid += 1
        d_topo.add_node(Node(13, "Surface Sink", "sink", 400, 400, 100, 100, 250))
        d_topo.auto_connect_reachable()
        save_configuration(d_topo, "dense_redundant_cluster.json")


class ConfigManager:
    """Convenience wrapper around configuration storage methods."""
    def __init__(self):
        ensure_sample_configs_exist()

    def get_configs_dir(self) -> str:
        return get_configs_dir()

    def save_config(self, topology: NetworkTopology, config_name: str) -> Tuple[bool, str, Optional[str]]:
        return save_configuration(topology, config_name)

    def load_config(self, filename_or_path: str) -> Tuple[Optional[NetworkTopology], str]:
        return load_configuration(filename_or_path)

    def list_saved_configs(self) -> List[Dict[str, Any]]:
        return list_saved_configurations()

