"""
build_corpus.py — build a knowledge graph from YOUR OWN documents.

The "feed it your corpus" entry point. Instead of searching the web for an
unfamiliar domain, this reads your files (notes, PDFs, book excerpts,
transcripts), extracts concepts + relations grounded in them, and produces the
same bilingual, themed, profiled graph the web pipeline does — but every concept
points back to the exact passage it came from.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python build_corpus.py --paths notes/ book.pdf lecture.txt \
        --title "My Reading on Stoicism" --lang en
    python export_html.py output/graph.json theme.json my_map.html
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os

from graph import KnowledgeGraph, biling
import pipeline
from corpus import load_corpus
from theme import design_theme


async def main(args):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    chunks = load_corpus(args.paths, target_chars=args.chunk_chars)
    if not chunks:
        raise SystemExit("No readable documents found in the given paths.")

    title = args.title or "My Knowledge Base"
    graph = KnowledgeGraph(expert=biling(title, title),
                           domain=biling("from documents", "源自文档"))

    langs = (args.lang,) if args.lang else ("en",)
    await pipeline.build_from_corpus(graph, chunks, expert_hint=args.title,
                                     langs=langs, concurrency=args.concurrency)
    await pipeline.resolve_entities(graph)
    meta = await pipeline.enrich(graph)
    await pipeline.profile_nodes(graph, langs=langs, top_only=args.profile_top)

    out = graph.to_dict()
    out["meta"] = meta
    out["lang_default"] = langs[0]
    out["source_mode"] = "corpus"   # so the dashboard can show provenance
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {graph.stats()} -> {args.out}")

    if not args.no_theme:
        theme = await design_theme(title, "personal knowledge base")
        with open(args.theme_out, "w", encoding="utf-8") as f:
            json.dump(theme.model_dump() if hasattr(theme, "model_dump") else theme,
                      f, ensure_ascii=False, indent=2)
        print(f"Theme '{getattr(theme,'name','?')}' -> {args.theme_out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="+", required=True,
                    help="files and/or directories to read")
    ap.add_argument("--title", default="", help="what the corpus is about")
    ap.add_argument("--lang", default="en", choices=["en", "zh"])
    ap.add_argument("--chunk-chars", type=int, default=2400)
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--profile-top", type=int, default=12,
                    help="profile only the N most central nodes (cost control)")
    ap.add_argument("--no-theme", action="store_true")
    ap.add_argument("--out", default="../output/graph.json")
    ap.add_argument("--theme-out", default="../output/theme.json")
    asyncio.run(main(ap.parse_args()))
