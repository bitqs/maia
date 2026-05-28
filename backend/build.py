"""
build.py — entry point (v2).

New in v2:
  --lang        primary language for prompts/console (en|zh), default en
  --depth/--nodes  OPTIONAL. If omitted, planner.assess_scope decides based
                   on the research subject.
  --subagent-seed  optional RNG seed for reproducible subagent routing.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    # let the tool decide depth from the subject:
    python build.py --expert "Laozi Dao De Jing" --domain "core concepts" --lang en
    # or pin it:
    python build.py --expert "Judea Pearl" --domain "causal inference" \
        --seeds "do-calculus,counterfactuals" --depth 2 --nodes 50

Interactive: if --expert/--domain are omitted, you'll be prompted.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os

from graph import KnowledgeGraph, biling
import pipeline
from planner import assess_scope, RelevanceScheduler


PROMPTS = {
    "en": {"expert": "Expert / body of knowledge: ",
           "domain": "Domain / sub-field: ",
           "lang": "Primary language [en/zh] (default en): ",
           "depth": "Search depth — blank = let the tool decide: "},
    "zh": {"expert": "专家 / 知识体系：",
           "domain": "领域 / 子方向：",
           "lang": "主要语言 [en/zh]（默认 en）：",
           "depth": "搜索深度——留空则由工具自行判定："},
}


async def main(args):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    lang = (args.lang or "en").lower()
    p = PROMPTS.get(lang, PROMPTS["en"])

    expert = args.expert or input(p["expert"]).strip()
    domain = args.domain or input(p["domain"]).strip()

    graph = KnowledgeGraph(expert=biling(expert, expert),
                           domain=biling(domain, domain))

    # --- depth: explicit or auto-assessed -------------------------------
    if args.depth and args.nodes:
        max_depth, max_nodes = args.depth, args.nodes
        print(f"[scope] using provided depth={max_depth}, nodes={max_nodes}")
    else:
        scope = await assess_scope(expert, domain)
        max_depth = args.depth or scope["max_depth"]
        max_nodes = args.nodes or scope["max_nodes"]
        rat = scope.get(f"rationale_{lang}") or scope.get("rationale_en")
        print(f"[scope] auto: {scope['scope']} -> depth={max_depth}, "
              f"nodes={max_nodes}  ({rat})")

    manual = [s.strip() for s in args.seeds.split(",") if s.strip()] \
        if args.seeds else None
    seeds = await pipeline.extract_seeds(expert, domain, manual)
    print(f"seeds: {[ (s['name'].get('en') if isinstance(s['name'],dict) else s['name']) for s in seeds]}")

    scheduler = RelevanceScheduler(seed=args.subagent_seed)
    # Wittgenstein: build both language-worlds independently; primary first.
    langs = ("en", "zh") if lang == "en" else ("zh", "en")
    await pipeline.expand(graph, seeds, max_depth=max_depth, max_nodes=max_nodes,
                          concurrency=args.concurrency, scheduler=scheduler,
                          langs=langs)
    await pipeline.resolve_entities(graph)
    meta = await pipeline.enrich(graph)
    await pipeline.profile_nodes(graph, langs=langs)

    out = graph.to_dict()
    out["meta"] = meta
    out["lang_default"] = lang
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {graph.stats()} -> {args.out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--expert", default="")
    ap.add_argument("--domain", default="")
    ap.add_argument("--lang", default="en", choices=["en", "zh"])
    ap.add_argument("--seeds", default="")
    ap.add_argument("--depth", type=int, default=0, help="0 = auto-assess")
    ap.add_argument("--nodes", type=int, default=0, help="0 = auto-assess")
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--subagent-seed", type=int, default=None)
    ap.add_argument("--out", default="../output/graph.json")
    asyncio.run(main(ap.parse_args()))
