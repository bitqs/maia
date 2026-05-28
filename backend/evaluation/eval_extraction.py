"""
eval_extraction.py — precision / recall / F1 against a gold set.

This is the cookbook's most important contribution and what the tool lacked
entirely: a FEEDBACK LOOP. Change an extraction prompt, rerun this, watch the
F1 move. That loop is what turns a demo into a production system.

Scores two things against a hand-labeled gold set:
  * concept recall (did we find the concepts that should be there?)
  * relation recall (did we find the right (source,target) links?
                     predicate wording is ignored, so this is an upper bound)

An alias map normalizes surface-form variants (and EN/ZH pairs) so that
"the Way" and "Dao" and "道" count as the same gold concept.

Usage:
    python evaluation/eval_extraction.py path/to/graph.json
    # defaults to ../../output/graph.json
"""
from __future__ import annotations
import json
import sys
from pathlib import Path


def _norm(name: str, aliases: dict) -> str:
    key = (name or "").strip().lower()
    return aliases.get(key, key)


def prf(predicted: set, gold: set):
    tp = len(predicted & gold)
    p = tp / len(predicted) if predicted else 0.0
    r = tp / len(gold) if gold else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def load_graph_names(graph: dict, aliases: dict):
    """Pull every node surface form (en + zh) and edge endpoint, normalized."""
    concepts = set()
    id_to_norm = {}
    for n in graph.get("nodes", []):
        forms = []
        nm = n.get("name", {})
        if isinstance(nm, dict):
            forms = [nm.get("en"), nm.get("zh")] + n.get("aliases", [])
        else:
            forms = [nm]
        norms = {_norm(f, aliases) for f in forms if f}
        concepts |= norms
        # pick a canonical normalized form for edge mapping
        id_to_norm[n["id"]] = next(iter(norms)) if norms else n["id"]
    relations = set()
    for e in graph.get("edges", []):
        s = id_to_norm.get(e["source"], e["source"])
        t = id_to_norm.get(e["target"], e["target"])
        relations.add((s, t))
    return concepts, relations


def main():
    here = Path(__file__).parent
    data_dir = here / "data"
    with open(data_dir / "gold.json", encoding="utf-8") as f:
        gold = json.load(f)
    with open(data_dir / "alias_map.json", encoding="utf-8") as f:
        aliases = json.load(f)

    graph_path = Path(sys.argv[1]) if len(sys.argv) > 1 else here / ".." / ".." / "output" / "graph.json"
    if not graph_path.exists():
        print(f"Graph not found: {graph_path}")
        print("Run build.py first, or pass a graph.json path.")
        sys.exit(1)
    with open(graph_path, encoding="utf-8") as f:
        graph = json.load(f)

    pred_concepts, pred_relations = load_graph_names(graph, aliases)

    gold_concepts = {_norm(c, aliases) for c in gold["concepts"]}
    gold_relations = {(_norm(s, aliases), _norm(t, aliases))
                      for s, t in (tuple(r) for r in gold["relations"])}

    cp, cr, cf = prf(pred_concepts, gold_concepts)
    rp, rr, rf = prf(pred_relations, gold_relations)

    print(f"Graph: {graph_path}")
    print(f"  predicted: {len(pred_concepts)} concepts, {len(pred_relations)} relations")
    print(f"  gold:      {len(gold_concepts)} concepts, {len(gold_relations)} relations\n")
    print(f"Concepts   P={cp:.2f}  R={cr:.2f}  F1={cf:.2f}")
    print(f"Relations  P={rp:.2f}  R={rr:.2f}  F1={rf:.2f}  (predicate-agnostic, upper bound)\n")

    missed_c = gold_concepts - pred_concepts
    if missed_c:
        print("Missed concepts:", ", ".join(sorted(missed_c)))
    missed_r = gold_relations - pred_relations
    if missed_r:
        print("Missed relations:", ", ".join(f"{s}->{t}" for s, t in sorted(missed_r)))
    extra_c = pred_concepts - gold_concepts
    if extra_c:
        print("Extra concepts (not in gold, may be fine):", ", ".join(sorted(extra_c)))


if __name__ == "__main__":
    main()
