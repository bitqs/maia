"""
pipeline.py — v3. Three philosophies fused:

  Cookbook (engineering):
    * structured Pydantic extraction instead of fragile JSON parsing
    * description carried into resolution to avoid same-name false merges
    * hub-node rich summaries

  Wittgenstein (epistemology) — "the limits of language are the limits of the
  world": the EN and ZH graphs are extracted INDEPENDENTLY (each language its
  own pass), then ALIGNED — not one graph machine-translated. Concepts and
  edges may differ slightly between the two worlds, and that difference is
  honest: translation has limits, so the two views are allowed to diverge.

  Jobs (taste) — handled in the dashboard, not here.

Stages:
  1 seeds         core concepts (bilingual)
  2 expand        per-language BFS, relevance-scored, subagent-routed
  3 align+resolve align EN/ZH worlds; merge synonyms using descriptions
  4 enrich        hub summaries + bilingual learning tour
"""
from __future__ import annotations
import asyncio
import json

from graph import KnowledgeGraph, biling, slugify
from clients import (parse_model, llm_json, web_search, Semaphored,
                     subagent_explore, SYNTHESIS_MODEL, EXTRACTION_MODEL)
from schemas import (ExtractedGraph, ResolvedClusters, HubProfile, TourPlan)
from planner import RelevanceScheduler


# ---------------------------------------------------------------------------
# STAGE 1 — seeds
# ---------------------------------------------------------------------------
async def extract_seeds(expert, domain, manual_seeds=None):
    if manual_seeds:
        return [biling(s, s) for s in manual_seeds]
    print("[stage 1] searching for seed concepts...")
    results = await web_search(f"{expert} {domain} foundational concepts", 6)
    corpus = "\n\n".join(f"{r['title']}\n{r['snippet']}" for r in results)
    g = await parse_model(
        f"""Material about {expert}'s work in {domain}:\n{corpus}\n
Extract 8-12 PILLAR concepts (central + distinctive, not generic).""",
        ExtractedGraph, model=EXTRACTION_MODEL)
    if not g:
        return []
    return [biling(c.name, c.name) for c in g.concepts]


# ---------------------------------------------------------------------------
# STAGE 2 — per-language expansion (Wittgenstein: two worlds)
# ---------------------------------------------------------------------------
async def _explore_lang(expert, domain, concept_name, lang):
    """Extract one concept's neighborhood IN ONE LANGUAGE via structured output.
    Searches in that language so the 'world' is genuinely that language's."""
    q = f"{expert} {domain} {concept_name}"
    if lang == "zh":
        q += " 解释 概念"
    results = await web_search(q, 4)
    sources = [r["url"] for r in results if r["url"]]
    corpus = "\n\n".join(f"{r['title']}\n{r['snippet']}" for r in results)
    instruction = (
        "Respond in Chinese for all names/descriptions." if lang == "zh"
        else "Respond in English for all names/descriptions.")
    g = await parse_model(
        f"""{instruction}
Material about "{concept_name}" within {expert}'s {domain}:
{corpus}

Extract this concept and its directly-related neighbors. For each concept give
a one-line description (used later to disambiguate). relevance 0-1 = how
central to {expert}'s {domain}. Mark generic/background concepts in_system=false
on their links.""",
        ExtractedGraph, model=EXTRACTION_MODEL)
    return g, sources


async def expand_world(graph, seeds, lang, max_depth, max_nodes,
                       concurrency, scheduler):
    """Build ONE language's graph. Returns nothing; fills `graph` in place,
    tagging every node with its language via the bilingual name half."""
    sem = Semaphored(concurrency)
    for s in seeds:
        nm = biling(s["en"], "") if lang == "en" else biling("", s["zh"])
        # seed name is bilingual already; use the matching half as display
        graph.add_node(s, depth=0, relevance=1.0)
    frontier = [(graph.add_node(s).id, 0) for s in seeds]

    while frontier:
        level = [(nid, d) for (nid, d) in frontier if d <= max_depth]
        frontier = []
        if not level or len(graph.nodes) >= max_nodes:
            break

        async def handle(nid, depth):
            node = graph.nodes[nid]
            name = node.name.get(lang) or node.name.get("en") or node.name.get("zh")
            parents = graph.in_degree(nid)
            rel = scheduler.combine(node.relevance, depth, parents, max_depth)
            node.relevance = round(rel, 3)
            use_sub = depth > 0 and scheduler.decide(rel)
            if use_sub:
                node.explored_by = "subagent"
                data = await subagent_explore(graph.expert.get("en"),
                                              graph.domain.get("en"), name, lang)
                return nid, ("sub", data), depth
            g, srcs = await _explore_lang(graph.expert.get("en"),
                                          graph.domain.get("en"), name, lang)
            return nid, ("main", g, srcs), depth

        outcomes = await asyncio.gather(*[sem.run(handle(n, d)) for (n, d) in level])

        for nid, payload, depth in outcomes:
            node = graph.nodes[nid]
            if payload[0] == "sub":
                data = payload[1]
                if not data:
                    continue
                summ = data.get("summary", {})
                if summ.get(lang):
                    node.summary[lang] = summ[lang]
                for url in data.get("sources", []):
                    if url and url not in node.sources:
                        node.sources.append(url)
                for nb in data.get("neighbors", []):
                    if not nb.get("in_system", False):
                        continue
                    if len(graph.nodes) >= max_nodes:
                        break
                    nb_name = nb["name"].get(lang) if isinstance(nb.get("name"), dict) else nb.get("name")
                    if not nb_name:
                        continue
                    nm = biling(nb_name, "") if lang == "en" else biling("", nb_name)
                    is_new = not graph.has_node(nm)
                    child = graph.add_node(nm, depth=depth+1,
                                           relevance=float(nb.get("relevance", 0.5)))
                    graph.add_edge(node.name, nm,
                                   biling(nb.get("relation", "depends_on"),
                                          nb.get("relation", "depends_on")),
                                   evidence=nb.get("evidence"))
                    if is_new and depth+1 <= max_depth:
                        frontier.append((child.id, depth+1))
            else:
                g, srcs = payload[1], payload[2]
                if not g:
                    continue
                # the first concept in the extraction is this node itself
                if g.concepts:
                    node.summary[lang] = g.concepts[0].description
                for url in srcs:
                    if url and url not in node.sources:
                        node.sources.append(url)
                # index concepts by name for description lookup
                cdesc = {c.name: (c.description, c.relevance, c.type) for c in g.concepts}
                for ln in g.links:
                    if not ln.in_system:
                        continue
                    if len(graph.nodes) >= max_nodes:
                        break
                    for endpoint in (ln.source, ln.target):
                        nm = biling(endpoint, "") if lang == "en" else biling("", endpoint)
                        if not graph.has_node(nm):
                            d, r, t = cdesc.get(endpoint, ("", ln.relevance, "concept"))
                            child = graph.add_node(nm, depth=depth+1, type=t,
                                                   relevance=float(r))
                            child.summary[lang] = d
                            if depth+1 <= max_depth:
                                frontier.append((child.id, depth+1))
                    s_nm = biling(ln.source, "") if lang == "en" else biling("", ln.source)
                    t_nm = biling(ln.target, "") if lang == "en" else biling("", ln.target)
                    graph.add_edge(s_nm, t_nm,
                                   biling(ln.relation, ln.relation),
                                   evidence=ln.evidence)
        print(f"  [{lang}] ...{graph.stats()}")


async def expand(graph, seeds, max_depth=2, max_nodes=60, concurrency=5,
                 scheduler=None, langs=("en", "zh")):
    """Run independent per-language expansions (the 'two worlds')."""
    sched = scheduler or RelevanceScheduler()
    print(f"[stage 2] expanding {len(langs)} language-worlds "
          f"(max_depth={max_depth}, max_nodes={max_nodes})...")
    # Each language gets its own node budget so neither starves the other.
    per_lang_cap = max(max_nodes // len(langs), 12)
    for lang in langs:
        print(f"  -- world: {lang} --")
        await expand_world(graph, seeds, lang, max_depth, per_lang_cap,
                           concurrency, sched)


# ---------------------------------------------------------------------------
# STAGE 3 — align worlds + resolve synonyms (cookbook description trick)
# ---------------------------------------------------------------------------
async def resolve_entities(graph):
    print("[stage 3] aligning language-worlds + resolving synonyms...")
    # Build entity list WITH descriptions (the cookbook's key disambiguator)
    items = []
    for n in graph.nodes.values():
        nm = n.name.get("en") or n.name.get("zh")
        desc = n.summary.get("en") or n.summary.get("zh") or ""
        items.append(f"- {nm}: {desc[:120]}")
    if len(items) < 2:
        return
    res = await parse_model(
        f"""Concepts from {graph.expert.get('en')}'s {graph.domain.get('en')} graph
(some are the same idea under different surface forms or across EN/ZH worlds):

{chr(10).join(items)}

Cluster same-meaning concepts. Each name appears in exactly one cluster.
Use the descriptions to avoid merging concepts that merely share a name.
Distinct concepts get their own single-element cluster. canonical = clearest form.""",
        ResolvedClusters, model=SYNTHESIS_MODEL, max_tokens=3000)
    if not res:
        return
    name_to_node = {}
    for n in graph.nodes.values():
        for half in (n.name.get("en"), n.name.get("zh")):
            if half:
                name_to_node[half] = n
    for cluster in res.clusters:
        members = [name_to_node[a] for a in cluster.aliases if a in name_to_node]
        members = list({m.id: m for m in members}.values())
        if len(members) < 2:
            continue
        keep = members[0]
        for drop in members[1:]:
            # before merging, fold ZH/EN halves so the kept node is bilingual
            for half in ("en", "zh"):
                if not keep.name.get(half) and drop.name.get(half):
                    keep.name[half] = drop.name[half]
                if not keep.summary.get(half) and drop.summary.get(half):
                    keep.summary[half] = drop.summary[half]
            graph.merge_nodes(keep.name, drop.name)
    print(f"  ...{graph.stats()} after alignment")


# ---------------------------------------------------------------------------
# STAGE 4 — hub summaries + bilingual tour
# ---------------------------------------------------------------------------
async def _summarize_hub(graph, node):
    nm = node.name.get("en") or node.name.get("zh")
    rels = []
    for e in graph.edges:
        if e.source == node.id:
            rels.append(f"{nm} --{e.relation.get('en')}--> {graph.nodes[e.target].name.get('en')}")
        elif e.target == node.id:
            rels.append(f"{graph.nodes[e.source].name.get('en')} --{e.relation.get('en')}--> {nm}")
    prof = await parse_model(
        f"""Profile this hub concept in {graph.expert.get('en')}'s {graph.domain.get('en')}.
Concept: {nm}
Current note: {node.summary.get('en','')}
Graph relations:
{chr(10).join(rels)}

Write a 2-sentence synthesized summary and 3 atomic key facts. Don't invent.""",
        HubProfile, model=SYNTHESIS_MODEL)
    if prof and prof.summary:
        node.summary["en"] = prof.summary
        node.tags = [biling(f, f) for f in prof.key_facts[:3]]


async def enrich(graph):
    print("[stage 4] hub summaries + learning tour...")
    foundational = graph.foundational_nodes(top=5)
    # rich profiles only for the top hubs (cost control, cookbook advice)
    hubs = sorted(graph.nodes.values(), key=lambda n: graph.in_degree(n.id),
                  reverse=True)[:3]
    await asyncio.gather(*[_summarize_hub(graph, h) for h in hubs])

    node_list = [{"id": n.id, "name": n.name.get("en") or n.name.get("zh"),
                  "in_degree": graph.in_degree(n.id), "relevance": n.relevance}
                 for n in graph.nodes.values()]
    plan = await parse_model(
        f"""Knowledge graph for {graph.expert.get('en')}'s {graph.domain.get('en')}.
Nodes: {json.dumps(node_list, ensure_ascii=False)}
Most depended-upon: {foundational}

Assign each node_id a difficulty, and produce "tour": an ordered learning path
of node_ids from bedrock to applications.""",
        TourPlan, model=SYNTHESIS_MODEL, max_tokens=2000)
    if plan:
        for nid, diff in plan.difficulty.items():
            if nid in graph.nodes:
                graph.nodes[nid].difficulty = diff
        tour = [t for t in plan.tour if t in graph.nodes]
    else:
        tour = foundational
    return {"foundational": foundational, "tour": tour}


# ---------------------------------------------------------------------------
# STAGE 5 — node profiling (the depth upgrade)
# ---------------------------------------------------------------------------
# This is what closes the gap with Understand-Anything's node inspector: every
# node gets a four-part ARCHIVE (what / why / position / key quote) instead of
# a one-line card. Generated per-language (Wittgenstein: each world its own),
# and grounded in the node's graph neighborhood so "position" is accurate.
from schemas import NodeProfile  # noqa: E402


async def _profile_node(graph, node, lang):
    nm = node.name.get(lang) or node.name.get("en") or node.name.get("zh")
    # neighborhood gives the model real material for the "position" part
    neighbors = []
    for e in graph.edges:
        if e.source == node.id:
            neighbors.append(f"{nm} --{e.relation.get(lang) or e.relation.get('en')}--> "
                             f"{graph.nodes[e.target].name.get(lang) or graph.nodes[e.target].name.get('en')}")
        elif e.target == node.id:
            neighbors.append(f"{graph.nodes[e.source].name.get(lang) or graph.nodes[e.source].name.get('en')} "
                             f"--{e.relation.get(lang) or e.relation.get('en')}--> {nm}")
    lang_instr = ("用中文回答所有字段。" if lang == "zh"
                  else "Answer all fields in English.")
    prof = await parse_model(
        f"""{lang_instr}
Write a four-part ARCHIVE for the concept "{nm}" in {graph.expert.get('en')}'s
{graph.domain.get('en')}. This is a teaching profile, not a dictionary entry.

Current note: {node.summary.get(lang, '')}
Its relations in the system:
{chr(10).join(neighbors) if neighbors else '(none recorded)'}

Fields:
- what: what this concept IS — 2-3 real sentences, not a one-liner.
- why: why it MATTERS within this body of knowledge.
- position: its PLACE in the system — what it grounds, what it depends on,
  using its actual relations above.
- quote: one key canonical quotation OR a concrete example that illuminates it.
- quote_source: where the quote/example comes from (chapter, work, etc.).
Ground everything in the real material; do not invent quotations.""",
        NodeProfile, model=SYNTHESIS_MODEL, max_tokens=1200)
    if not prof:
        return
    for part in ("what", "why", "position", "quote"):
        node.profile.setdefault(part, {"en": "", "zh": ""})
        node.profile[part][lang] = getattr(prof, part, "") or node.profile[part].get(lang, "")
    if prof.quote_source and not node.profile.get("quote_source"):
        node.profile["quote_source"] = prof.quote_source


async def profile_nodes(graph, langs=("en", "zh"), concurrency=5,
                        top_only=None):
    """Generate four-part archives. top_only=N profiles only the N most central
    nodes (cost control); None profiles all."""
    print("[stage 5] profiling nodes (four-part archive)...")
    sem = Semaphored(concurrency)
    nodes = list(graph.nodes.values())
    if top_only:
        nodes = sorted(nodes, key=lambda n: graph.in_degree(n.id),
                       reverse=True)[:top_only]
    tasks = []
    for node in nodes:
        for lang in langs:
            tasks.append(sem.run(_profile_node(graph, node, lang)))
    await asyncio.gather(*tasks)
    print(f"  ...profiled {len(nodes)} nodes x {len(langs)} languages")


# ===========================================================================
# DOCUMENT MODE — build a graph from YOUR corpus instead of web search.
# ===========================================================================
# This is the cookbook's native scenario: extract entities+relations from each
# chunk with structured output, resolve surface forms, assemble. Every concept
# keeps chunk provenance so the graph points back to the exact passage.
from schemas import DocExtraction  # noqa: E402


async def _extract_chunk(chunk, expert_hint, lang):
    lang_instr = ("用中文回答所有名称与描述。" if lang == "zh"
                  else "Answer all names and descriptions in English.")
    hint = f" The corpus concerns: {expert_hint}." if expert_hint else ""
    data = await parse_model(
        f"""{lang_instr}
Extract a knowledge graph from this passage.{hint}

<passage id="{chunk.id}">
{chunk.text}
</passage>

Guidelines:
- Extract only concepts CENTRAL to the passage; skip incidental mentions.
- One-line description per concept (used later to disambiguate).
- relevance 0-1 = how central the concept is to the passage's topic.
- Relations: short relation type between two concepts you extracted.
- Set chunk_ids/chunk_id to "{chunk.id}" for traceability.""",
        DocExtraction, model=EXTRACTION_MODEL, max_tokens=2048)
    return chunk, data


async def build_from_corpus(graph, chunks, expert_hint="", langs=("en",),
                            concurrency=5):
    """Build the graph by extracting from document chunks (cookbook pattern).
    Runs one language at a time; en is the practical default for most corpora,
    but zh works identically for Chinese documents."""
    print(f"[doc-mode] extracting from {len(chunks)} chunks "
          f"({len(langs)} language(s))...")
    sem = Semaphored(concurrency)
    for lang in langs:
        tasks = [sem.run(_extract_chunk(c, expert_hint, lang)) for c in chunks]
        results = await asyncio.gather(*tasks)
        for chunk, data in results:
            if not data:
                continue
            cdesc = {}
            for c in data.concepts:
                nm = biling(c.name, "") if lang == "en" else biling("", c.name)
                node = graph.add_node(nm, type=c.type,
                                      relevance=float(c.relevance))
                if c.description and not node.summary.get(lang):
                    node.summary[lang] = c.description
                # provenance: which chunk(s) this concept came from
                for cid in (c.chunk_ids or [chunk.id]):
                    if cid not in node.sources:
                        node.sources.append(cid)
                cdesc[c.name] = c.description
            for ln in data.links:
                s_nm = biling(ln.source, "") if lang == "en" else biling("", ln.source)
                t_nm = biling(ln.target, "") if lang == "en" else biling("", ln.target)
                # only link concepts we actually extracted
                if not (graph.has_node(s_nm) and graph.has_node(t_nm)):
                    continue
                graph.add_edge(s_nm, t_nm,
                               biling(ln.relation, ln.relation),
                               evidence=ln.evidence or (chunk.id))
        print(f"  [doc-mode/{lang}] ...{graph.stats()}")
