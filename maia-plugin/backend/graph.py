"""
graph.py — Knowledge graph data structures (BILINGUAL upgrade).

Changes from v1:
  * Every human-readable field (name, summary, tags, relation) is now a
    {"en": ..., "zh": ...} dict instead of a plain string.
  * Node carries `relevance` (0-1, how central to the expert's system) used
    by the subagent scheduler in pipeline.py.
The graph remains the single contract; everything else fills into it.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


def biling(en: str = "", zh: str = "") -> dict:
    return {"en": en.strip(), "zh": zh.strip()}


def slugify(name) -> str:
    """Stable id from the EN side of a bilingual name (fallback zh)."""
    if isinstance(name, dict):
        name = name.get("en") or name.get("zh") or ""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    return s.strip("-")


@dataclass
class Node:
    id: str
    name: dict
    type: str = "concept"
    summary: dict = field(default_factory=biling)
    tags: list = field(default_factory=list)
    difficulty: Optional[str] = None
    relevance: float = 1.0
    sources: list = field(default_factory=list)
    depth: int = 0
    aliases: list = field(default_factory=list)
    explored_by: str = "main"
    # the four-part archive, each part bilingual: {"what":{en,zh}, "why":{...}, ...}
    profile: dict = field(default_factory=lambda: {
        "what": {"en": "", "zh": ""}, "why": {"en": "", "zh": ""},
        "position": {"en": "", "zh": ""},
        "quote": {"en": "", "zh": ""}, "quote_source": ""})


@dataclass
class Edge:
    source: str
    target: str
    relation: dict = field(default_factory=biling)
    evidence: Optional[str] = None


class KnowledgeGraph:
    def __init__(self, expert, domain):
        self.expert = expert if isinstance(expert, dict) else biling(expert, expert)
        self.domain = domain if isinstance(domain, dict) else biling(domain, domain)
        self.nodes: dict = {}
        self.edges: list = []

    def add_node(self, name, **kwargs) -> Node:
        nm = name if isinstance(name, dict) else biling(name, name)
        nid = slugify(nm)
        if nid in self.nodes:
            node = self.nodes[nid]
            for url in kwargs.get("sources", []) or []:
                if url not in node.sources:
                    node.sources.append(url)
            if "depth" in kwargs:
                node.depth = min(node.depth, kwargs["depth"])
            for half in ("en", "zh"):
                if not node.name.get(half) and nm.get(half):
                    node.name[half] = nm[half]
            return node
        kwargs.pop("sources", None)
        node = Node(id=nid, name=nm, **kwargs)
        self.nodes[nid] = node
        return node

    def has_node(self, name) -> bool:
        return slugify(name) in self.nodes

    def add_edge(self, source, target, relation, evidence=None) -> None:
        s, t = slugify(source), slugify(target)
        if s == t:
            return
        rel = relation if isinstance(relation, dict) else biling(relation, relation)
        for e in self.edges:
            if e.source == s and e.target == t and e.relation.get("en") == rel.get("en"):
                return
        self.edges.append(Edge(source=s, target=t, relation=rel, evidence=evidence))

    def merge_nodes(self, keep, drop) -> None:
        keep_id, drop_id = slugify(keep), slugify(drop)
        if keep_id not in self.nodes or drop_id not in self.nodes or keep_id == drop_id:
            return
        k, d = self.nodes[keep_id], self.nodes[drop_id]
        k.aliases.append(d.name.get("en") or d.name.get("zh"))
        k.aliases.extend(d.aliases)
        for url in d.sources:
            if url not in k.sources:
                k.sources.append(url)
        for half in ("en", "zh"):
            if not k.name.get(half) and d.name.get(half):
                k.name[half] = d.name[half]
        for e in self.edges:
            if e.source == drop_id:
                e.source = keep_id
            if e.target == drop_id:
                e.target = keep_id
        del self.nodes[drop_id]
        seen, cleaned = set(), []
        for e in self.edges:
            if e.source == e.target:
                continue
            key = (e.source, e.target, e.relation.get("en"))
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(e)
        self.edges = cleaned

    def in_degree(self, node_id: str) -> int:
        return sum(1 for e in self.edges if e.target == node_id)

    def out_degree(self, node_id: str) -> int:
        return sum(1 for e in self.edges if e.source == node_id)

    def foundational_nodes(self, top: int = 5) -> list:
        return sorted(self.nodes, key=self.in_degree, reverse=True)[:top]

    def to_dict(self) -> dict:
        return {
            "schema": "bilingual-v2",
            "expert": self.expert,
            "domain": self.domain,
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def stats(self) -> str:
        sub = sum(1 for n in self.nodes.values() if n.explored_by == "subagent")
        return f"{len(self.nodes)} nodes ({sub} via subagent), {len(self.edges)} edges"
