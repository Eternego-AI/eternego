"""Memory — the cognitive graph.

Single shared store for all cognitive state. All modules read from and write to it.
Nodes are Signal, Perception, or Thought. Edges are typed directed relationships.

Edge types:
  perceived_as    Signal → Perception      signal formally belongs to this perception
  routed_to       Signal → Perception      authorize hint (realize confirms)
  proposed_for    Perception → Perception  experience: proposal targets original
  planned_for     Thought → Perception     think: this thought addresses this perception
  output_of       Signal → Thought         do: tool result linked to producing thought
"""

import json
from dataclasses import dataclass, field
from datetime import datetime

from application.core.brain.data import Signal, Perception, Thought, Step
from application.platform import datetimes, filesystem, logger


@dataclass
class Edge:
    src_id: str
    dst_id: str
    type: str
    created_at: datetime = field(default_factory=datetimes.now)


class Memory:

    def __init__(self, persona_id: str):
        self._persona_id = persona_id
        self.nodes: dict[str, Signal | Perception | Thought] = {}
        self.edges: list[Edge] = []

    # --- Typed views ---

    def signals(self) -> list[Signal]:
        return [n for n in self.nodes.values() if isinstance(n, Signal)]

    def perceptions(self) -> list[Perception]:
        return [n for n in self.nodes.values() if isinstance(n, Perception)]

    def thoughts(self) -> list[Thought]:
        return [n for n in self.nodes.values() if isinstance(n, Thought)]

    # --- Graph operations ---

    def add_node(self, node: Signal | Perception | Thought) -> None:
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        self.edges = [e for e in self.edges
                      if e.src_id != node_id and e.dst_id != node_id]

    def add_edge(self, src_id: str, dst_id: str, type: str) -> None:
        for e in self.edges:
            if e.src_id == src_id and e.dst_id == dst_id and e.type == type:
                return  # already exists
        self.edges.append(Edge(src_id=src_id, dst_id=dst_id, type=type))

    def remove_edge(self, src_id: str, dst_id: str, type: str) -> None:
        self.edges = [e for e in self.edges
                      if not (e.src_id == src_id and e.dst_id == dst_id and e.type == type)]

    def outgoing(self, node_id: str, type: str) -> list:
        return [self.nodes[e.dst_id] for e in self.edges
                if e.src_id == node_id and e.type == type and e.dst_id in self.nodes]

    def incoming(self, node_id: str, type: str) -> list:
        return [self.nodes[e.src_id] for e in self.edges
                if e.dst_id == node_id and e.type == type and e.src_id in self.nodes]

    def has_outgoing(self, node_id: str, type: str) -> bool:
        return any(e.src_id == node_id and e.type == type and e.dst_id in self.nodes
                   for e in self.edges)

    def has_incoming(self, node_id: str, type: str) -> bool:
        return any(e.dst_id == node_id and e.type == type and e.src_id in self.nodes
                   for e in self.edges)

    # --- Persistence ---

    def persist(self) -> None:
        from application.core import paths
        path = paths.mind_state(self._persona_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        data: dict = {"nodes": [], "edges": []}

        for node in self.nodes.values():
            if isinstance(node, Signal):
                data["nodes"].append({
                    "shape": "signal",
                    "id": node.id,
                    "role": node.role,
                    "data": node.data,
                    "created_at": node.created_at.isoformat(),
                    "processed_at": node.processed_at.isoformat() if node.processed_at else None,
                })
            elif isinstance(node, Perception):
                data["nodes"].append({
                    "shape": "perception",
                    "id": node.id,
                    "signals": [_serialize_signal(s) for s in node.signals],
                    "impression": node.impression,
                    "meaning": node.meaning,
                    "completed": node.completed,
                    "created_at": node.created_at.isoformat(),
                })
            elif isinstance(node, Thought):
                data["nodes"].append({
                    "shape": "thought",
                    "id": node.id,
                    "perception_id": node.perception_id,
                    "steps": [
                        {"number": s.number, "tool": s.tool, "params": s.params}
                        for s in node.steps
                    ],
                    "authorized": node.authorized,
                    "pending_tools": node.pending_tools,
                    "completed_at": node.completed_at.isoformat() if node.completed_at else None,
                    "created_at": node.created_at.isoformat(),
                })

        for edge in self.edges:
            data["edges"].append({
                "src_id": edge.src_id,
                "dst_id": edge.dst_id,
                "type": edge.type,
                "created_at": edge.created_at.isoformat(),
            })

        filesystem.write_json(path, data)
        logger.info("memory.persist", {
            "persona_id": self._persona_id,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
        })

    def load(self) -> None:
        from application.core import paths
        path = paths.mind_state(self._persona_id)
        if not path.exists():
            return

        try:
            data = filesystem.read_json(path)
            if not data:
                return
        except Exception as e:
            logger.warning("memory.load: failed to read", {
                "persona_id": self._persona_id, "error": str(e)
            })
            return

        for item in data.get("nodes", []):
            shape = item.get("shape")
            try:
                if shape == "signal":
                    self.nodes[item["id"]] = _deserialize_signal(item)
                elif shape == "perception":
                    signals = [_deserialize_signal(s) for s in item.get("signals", [])]
                    self.nodes[item["id"]] = Perception(
                        signals=signals,
                        id=item["id"],
                        created_at=datetime.fromisoformat(item["created_at"]),
                        impression=item.get("impression"),
                        meaning=item.get("meaning"),
                        completed=item.get("completed", False),
                    )
                elif shape == "thought":
                    steps = [
                        Step(number=s["number"], tool=s["tool"], params=s["params"])
                        for s in item.get("steps", [])
                    ]
                    raw_completed = item.get("completed_at")
                    self.nodes[item["id"]] = Thought(
                        perception_id=item["perception_id"],
                        steps=steps,
                        id=item["id"],
                        created_at=datetime.fromisoformat(item["created_at"]),
                        authorized=item.get("authorized", False),
                        pending_tools=item.get("pending_tools", []),
                        completed_at=datetime.fromisoformat(raw_completed) if raw_completed else None,
                    )
            except Exception as e:
                logger.warning("memory.load: skipping node", {
                    "shape": shape, "error": str(e)
                })

        for item in data.get("edges", []):
            try:
                self.edges.append(Edge(
                    src_id=item["src_id"],
                    dst_id=item["dst_id"],
                    type=item["type"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                ))
            except Exception as e:
                logger.warning("memory.load: skipping edge", {"error": str(e)})

        logger.info("memory.load", {
            "persona_id": self._persona_id,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
        })

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self.persist()


def _serialize_signal(s: Signal) -> dict:
    return {
        "id": s.id,
        "role": s.role,
        "data": s.data,
        "created_at": s.created_at.isoformat(),
        "processed_at": s.processed_at.isoformat() if s.processed_at else None,
    }


def _deserialize_signal(item: dict) -> Signal:
    """Deserialize a signal dict, handling both new format (data dict) and legacy format (content str)."""
    if "data" in item:
        data_dict = item["data"]
    else:
        # Legacy format: had role + content at top level
        data_dict = {"content": item.get("content", "")}

    raw_processed = item.get("processed_at")
    return Signal(
        role=item["role"],
        data=data_dict,
        id=item["id"],
        created_at=datetime.fromisoformat(item["created_at"]),
        processed_at=datetime.fromisoformat(raw_processed) if raw_processed else None,
    )
