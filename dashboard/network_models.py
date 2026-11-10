"""
network_models.py - Core data models and validation logic for AquaNet 3D Network Builder.
Project: Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning
Module: Network Builder Data Layer
"""

import math
from typing import Dict, List, Tuple, Optional, Any


class Node:
    """Represents an acoustic sensor, source, or sink entity in the underwater volume."""
    def __init__(
        self,
        node_id: int,
        name: str,
        node_type: str = "sensor",
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        initial_energy: float = 100.0,
        tx_range: float = 250.0,
        status: str = "Operational",
        notes: str = ""
    ):
        self.id = int(node_id)
        self.name = str(name)
        self.type = str(node_type).lower()  # 'source', 'sensor', 'sink', 'sensor_failed'
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)  # Reflected elevation in meters (depth from surface is 100 - z)
        self.initial_energy = float(initial_energy)
        self.tx_range = float(tx_range)
        self.status = str(status)
        self.notes = str(notes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "z": round(self.z, 2),
            "initial_energy": round(self.initial_energy, 2),
            "tx_range": round(self.tx_range, 2),
            "status": self.status,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Node":
        return cls(
            node_id=d.get("id", 0),
            name=d.get("name", f"Node {d.get('id', 0)}"),
            node_type=d.get("type", "sensor"),
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            z=d.get("z", 0.0),
            initial_energy=d.get("initial_energy", 100.0),
            tx_range=d.get("tx_range", 250.0),
            status=d.get("status", "Operational"),
            notes=d.get("notes", "")
        )

    def distance_to(self, other: "Node") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)


class NetworkTopology:
    """Manages the underwater wireless sensor network graph topology."""
    def __init__(self, name: str = "AquaNet Topology", description: str = ""):
        self.name = name
        self.description = description
        self.nodes: Dict[int, Node] = {}
        self.links: List[Tuple[int, int]] = []  # List of unique sorted (u, v) pairs

    def add_node(self, node: Node) -> bool:
        if node.id in self.nodes:
            return False
        self.nodes[node.id] = node
        return True

    def remove_node(self, node_id: int) -> bool:
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        # Remove any attached links
        self.links = [link for link in self.links if node_id not in link]
        return True

    def update_node(self, node_id: int, **kwargs) -> bool:
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        for k, v in kwargs.items():
            if hasattr(node, k):
                setattr(node, k, v)
        return True

    def add_link(self, u: int, v: int) -> bool:
        if u == v or u not in self.nodes or v not in self.nodes:
            return False
        link_pair = (min(u, v), max(u, v))
        if link_pair not in self.links:
            self.links.append(link_pair)
            return True
        return False

    def remove_link(self, u: int, v: int) -> bool:
        link_pair = (min(u, v), max(u, v))
        if link_pair in self.links:
            self.links.remove(link_pair)
            return True
        return False

    def clear_links(self):
        self.links = []

    def auto_connect_reachable(self) -> int:
        """Connects all node pairs whose Euclidean distance is within communication range."""
        added = 0
        node_ids = sorted(self.nodes.keys())
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                u, v = node_ids[i], node_ids[j]
                n1, n2 = self.nodes[u], self.nodes[v]
                dist = n1.distance_to(n2)
                # Link is reachable if distance <= min of both transmission ranges
                max_reach = min(n1.tx_range, n2.tx_range)
                if dist <= max_reach:
                    if self.add_link(u, v):
                        added += 1
        return added

    def get_source_node(self) -> Optional[Node]:
        for n in self.nodes.values():
            if n.type == "source":
                return n
        return None

    def get_sink_node(self) -> Optional[Node]:
        for n in self.nodes.values():
            if n.type == "sink":
                return n
        return None

    def set_source_node(self, node_id: int) -> bool:
        if node_id not in self.nodes:
            return False
        # Remove previous source designation
        for n in self.nodes.values():
            if n.type == "source":
                n.type = "sensor"
        self.nodes[node_id].type = "source"
        return True

    def set_sink_node(self, node_id: int) -> bool:
        if node_id not in self.nodes:
            return False
        # Remove previous sink designation
        for n in self.nodes.values():
            if n.type == "sink":
                n.type = "sensor"
        self.nodes[node_id].type = "sink"
        return True

    def get_bounding_box(self) -> Dict[str, float]:
        if not self.nodes:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}
        xs = [n.x for n in self.nodes.values()]
        ys = [n.y for n in self.nodes.values()]
        zs = [n.z for n in self.nodes.values()]
        return {
            "min_x": min(xs), "max_x": max(xs),
            "min_y": min(ys), "max_y": max(ys),
            "min_z": min(zs), "max_z": max(zs)
        }

    def get_link_details(self) -> List[Dict[str, Any]]:
        details = []
        for u, v in sorted(self.links):
            if u in self.nodes and v in self.nodes:
                n1, n2 = self.nodes[u], self.nodes[v]
                dist = n1.distance_to(n2)
                max_reach = min(n1.tx_range, n2.tx_range)
                is_within = dist <= max_reach
                details.append({
                    "u": u,
                    "v": v,
                    "label": f"Node {u} <---> Node {v}",
                    "distance": round(dist, 2),
                    "max_range": round(max_reach, 2),
                    "is_within_range": is_within,
                    "involves_failed": (n1.type == "sensor_failed" or n2.type == "sensor_failed")
                })
        return details

    def validate(self) -> Tuple[bool, List[str]]:
        issues = []
        if not self.nodes:
            issues.append("Network has no nodes.")
            return False, issues

        sources = [n for n in self.nodes.values() if n.type == "source"]
        sinks = [n for n in self.nodes.values() if n.type == "sink"]

        if len(sources) == 0:
            issues.append("No source node designated. Please assign at least one source.")
        elif len(sources) > 1:
            issues.append(f"Multiple source nodes configured ({[n.id for n in sources]}). Standard UWSN setup requires 1 source.")

        if len(sinks) == 0:
            issues.append("No sink node designated. Please assign at least one sink.")
        elif len(sinks) > 1:
            issues.append(f"Multiple sink nodes configured ({[n.id for n in sinks]}). Standard UWSN setup requires 1 surface sink.")

        if sources and sinks and sources[0].id == sinks[0].id:
            issues.append(f"Node {sources[0].id} cannot be designated as both Source and Sink.")

        # Check for isolated nodes
        connected_ids = set()
        for u, v in self.links:
            connected_ids.add(u)
            connected_ids.add(v)
        isolated = [nid for nid in self.nodes if nid not in connected_ids]
        if isolated and len(self.nodes) > 1:
            issues.append(f"Isolated node(s) with no links: Node {isolated}")

        is_valid = (len(sources) == 1 and len(sinks) == 1 and sources[0].id != sinks[0].id)
        return is_valid, issues

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "links": [{"u": u, "v": v} for u, v in sorted(self.links)]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NetworkTopology":
        topo = cls(
            name=d.get("name", "Imported Topology"),
            description=d.get("description", "")
        )
        for n_dict in d.get("nodes", []):
            node = Node.from_dict(n_dict)
            topo.add_node(node)
        for l_dict in d.get("links", []):
            topo.add_link(l_dict.get("u", 0), l_dict.get("v", 0))
        return topo


def get_default_project_topology() -> NetworkTopology:
    """
    Returns the exact verified 12-node reflected topology from scratch/underwater-network.cc:
    - Seafloor Source: Node 12 at (50, 50, 0)
    - Sensors 1 to 10: (90 + 40i, 90 + 40i, 10 + 8i)
    - Failure Subject: Sensor 5 at (250, 250, 42)
    - Surface Gateway: Node 11 at (500, 500, 100)
    - Acoustic Range: 250 m | Initial Energy: 100.0 J
    """
    topo = NetworkTopology(
        name="Authoritative NS-3.41 Reflected Topology",
        description="Verified 12-node inclined acoustic corridor with Sensor 5 failure at t = 50.0s."
    )

    # Source Node (Node 12)
    topo.add_node(Node(
        node_id=12,
        name="Source Node (Node 12)",
        node_type="source",
        x=50.0,
        y=50.0,
        z=0.0,
        initial_energy=100.0,
        tx_range=250.0,
        status="Operational",
        notes="Seafloor application traffic generator"
    ))

    # Sensor Nodes (Nodes 1 to 10)
    for i in range(10):
        sensor_num = i + 1
        x = 90.0 + i * 40.0
        y = 90.0 + i * 40.0
        z = 10.0 + i * 8.0
        is_s5 = (sensor_num == 5)

        topo.add_node(Node(
            node_id=sensor_num,
            name=f"Sensor {sensor_num}",
            node_type="sensor_failed" if is_s5 else "sensor",
            x=x,
            y=y,
            z=z,
            initial_energy=100.0,
            tx_range=250.0,
            status="Scheduled Failure at 50.0s" if is_s5 else "Operational",
            notes="Scheduled failure subject" if is_s5 else "Intermediate acoustic relay"
        ))

    # Surface Sink Node (Node 11)
    topo.add_node(Node(
        node_id=11,
        name="Surface Sink (Node 11)",
        node_type="sink",
        x=500.0,
        y=500.0,
        z=100.0,
        initial_energy=100.0,
        tx_range=250.0,
        status="Operational",
        notes="Surface gateway data collector"
    ))

    # Connect geometrically reachable links within 250 m
    topo.auto_connect_reachable()
    return topo
