"""validate.py — normalize graph.json produced by the skill."""

import json
import re
import sys
from pathlib import Path


def slugify(name):
    if isinstance(name, dict):
        name = name.get("en") or name.get("zh") or ""
    s = str(name).strip().lower()
    s = re.sub(r"[^a-z0-9一-鿿]+", "-", s)
    return s.strip("-")


def biling(en="", zh=""):
    return {"en": en, "zh": zh}


def main():
    if len(sys.argv) < 2:
        print("Usage: validate.py <graph.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    try:
        g = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to parse {path}: {e}")
        sys.exit(1)

    # Normalize nodes
    id_map = {}
    seen_ids = set()
    new_nodes = []
    for node in g.get("nodes", []):
        old_id = node.get("id", "")
        new_id = slugify(node.get("name", old_id)) or slugify(old_id)
        if not new_id:
            continue
        # handle duplicates by appending counter
        base, counter = new_id, 2
        while new_id in seen_ids:
            new_id = f"{base}-{counter}"
            counter += 1
        id_map[old_id] = new_id
        node["id"] = new_id
        seen_ids.add(new_id)

        # ensure required fields
        node.setdefault("name", biling())
        if not isinstance(node["name"], dict):
            node["name"] = biling(str(node["name"]))
        node.setdefault("type", "concept")
        node.setdefault("summary", biling())
        if not isinstance(node["summary"], dict):
            node["summary"] = biling(str(node["summary"]))
        node.setdefault("tags", [])
        node.setdefault("difficulty", None)
        node.setdefault("relevance", 0.8)
        node.setdefault("sources", [])
        node.setdefault("depth", 0)
        node.setdefault("aliases", [])
        node.setdefault("explored_by", "main")
        node.setdefault("profile", {})
        for part in ("what", "why", "position", "quote"):
            node["profile"].setdefault(part, biling())
            if not isinstance(node["profile"][part], dict):
                node["profile"][part] = biling(str(node["profile"][part]))
        node["profile"].setdefault("quote_source", "")

        new_nodes.append(node)

    g["nodes"] = new_nodes
    valid_ids = seen_ids

    # Normalize edges
    seen_edges = set()
    new_edges = []
    for edge in g.get("edges", []):
        src = id_map.get(edge.get("source", ""), edge.get("source", ""))
        tgt = id_map.get(edge.get("target", ""), edge.get("target", ""))
        if src not in valid_ids or tgt not in valid_ids or src == tgt:
            continue
        key = (src, tgt)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edge["source"] = src
        edge["target"] = tgt
        if not isinstance(edge.get("relation"), dict):
            edge["relation"] = biling(str(edge.get("relation", "depends_on")))
        edge.setdefault("evidence", None)
        new_edges.append(edge)
    g["edges"] = new_edges

    # Fix meta
    meta = g.get("meta", {})
    remap = lambda ids: [id_map.get(i, i) for i in ids if id_map.get(i, i) in valid_ids]
    meta["foundational"] = remap(meta.get("foundational", []))
    meta["tour"] = remap(meta.get("tour", []))
    if not meta["foundational"]:
        meta["foundational"] = list(valid_ids)[:5]
    if not meta["tour"]:
        meta["tour"] = list(valid_ids)
    g["meta"] = meta

    g.setdefault("schema", "bilingual-v2")
    g.setdefault("lang_default", "en")

    path.write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(g['nodes'])} nodes, {len(g['edges'])} edges → {path}")


if __name__ == "__main__":
    main()
