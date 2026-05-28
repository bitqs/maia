<div align="center">

# Maia

### *graphs that teach.*

**Turn any body of knowledge into a living map that explains itself.**

Point Maia at a thinker, a field, or your own notes — it builds an interactive,
bilingual concept graph where every idea carries a full archive (*what it is ·
why it matters · where it sits · a key line*), arranges itself in a visual
identity chosen to fit the subject, and walks you through it like a patient teacher.

[Quickstart](#quickstart) · [What makes it different](#what-makes-it-different) · [How it works](#how-it-works) · [Gallery](#gallery)

</div>

---

> Maia is named for the midwife-goddess behind Socrates' *maieutics* — the art of
> drawing understanding out of someone rather than pouring it in. That is the whole
> idea: Maia doesn't hand you a pile of nodes, it builds a map and leads you through
> until the understanding is *yours*.

## Why

You want to understand something — Stoicism, causal inference, the Daodejing, a
stack of papers you've been meaning to read. The usual options:

- **Search** gives you ten tabs and no shape.
- **A summary** flattens a system into a paragraph and loses every connection.
- **A raw knowledge graph** gives you a pretty hairball you can't actually learn from.

Maia gives you the thing in between: a **map that teaches**. Concepts you can
*see* arranged by importance, *read* in depth, and *walk* in the right order —
from bedrock ideas up to the ones that depend on them.

## What makes it different

Most "knowledge graph" tools stop at *impressive*. Maia is built around three
convictions that make it *teach*:

| | |
|---|---|
| 🧭 **Graphs that teach, not impress** | Every node is a four-part **archive** — what it is, why it matters, its place in the system, and a key quotation — not a one-line label. A built-in **guided tour** orders concepts from foundations upward, like a teacher walking you through. |
| 🌏 **Two languages, two worlds** | Following Wittgenstein — *"the limits of my language are the limits of my world"* — the English and Chinese graphs are extracted **independently**, then aligned. Switching language switches *worldview*, not just labels. |
| 🎨 **Taste, applied per subject** | A Daodejing map and a quantum-mechanics map should not look the same. Maia reads a subject's *character* (classical↔modern, eastern↔western, intuitive↔rational…) and **designs a visual identity to fit** — ink-wash, blueprint, editorial — within a hard floor of legibility. |
| 📄 **Feeds on your own knowledge** | Beyond web research, point Maia at your **own documents** (`.md .txt .pdf .docx`). Every concept traces back to the exact passage it came from, and ideas that never share a page get connected across your library. |
| 🪶 **One file, double-click to open** | Export the whole thing as a **single self-contained `.html`** — no server, no build, no network. Fullscreen-adaptive for presentation. Share it like a PDF. |
| 📐 **An evaluation loop, not vibes** | A precision/recall harness scores extraction against a gold set, so you can change a prompt and *watch the F1 move* — the discipline that turns a demo into a tool. |

## Quickstart

```bash
git clone https://github.com/bitqs/maia && cd maia/maia-plugin/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

**Map a subject** (Maia researches it):

```bash
python build.py --expert "Laozi Daodejing" --domain "core concepts" --lang en
python export_html.py ../output/graph.json ../output/theme.json daodejing.html
open daodejing.html
```

**Map your own documents** (Maia reads them):

```bash
python build_corpus.py --paths ./notes ./book.pdf --title "My Reading on Stoicism"
python export_html.py ../output/graph.json ../output/theme.json mine.html
```

Don't specify a depth and Maia decides one from the subject — a single classic
text gets a shallow, complete map; a sprawling field gets a deeper, more
aggressively filtered one.

## How it works

```
  subject  or  your documents
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │  1  seed / read     find pillar concepts      │
  │  2  expand          per-language worlds,       │
  │                     low-relevance concepts     │
  │                     explored by isolated       │
  │                     sub-agents (kept out of    │
  │                     the main context)          │
  │  3  align + resolve  merge synonyms across      │
  │                     EN/ZH using descriptions   │
  │  4  enrich          hubs, difficulty, tour     │
  │  5  profile         the four-part archive      │
  │  6  theme           a visual identity for the  │
  │                     subject's character        │
  └─────────────────────────────────────────────┘
        │
        ▼
   graph.json  ──►  self-contained .html  ──►  evaluation/
```

A few design choices worth calling out:

- **Relevance-routed sub-agents.** Each concept gets a relevance score (the model's
  judgement fused with graph structure). The *lower* the relevance, the *higher* the
  chance it's explored by an isolated sub-agent — so peripheral, possibly-off-topic
  ideas do their wandering in a separate context and report back only a verdict,
  keeping the main graph clean. Probabilistic, not a hard cutoff, so it degrades
  gracefully.
- **Structured outputs everywhere.** Extraction uses validated Pydantic schemas, not
  hand-parsed JSON — no regex, no decode errors.
- **Two models, by job.** A fast model does high-volume extraction; a stronger one
  does resolution and synthesis, where evidence must be weighed.

## Gallery

The same engine, three subjects, three identities it chose for itself:

| Subject | Identity | Why |
|---|---|---|
| Laozi — *Daodejing* | **ink-wash** — warm dark paper, brush serif, water-curved lines | classical · eastern · intuitive · organic |
| Quantum Mechanics | **blueprint** — slate-navy, mono type, grid, straight edges | modern · technical · rational · geometric |
| Renaissance Painting | **editorial** — warm gallery white, transitional serif, arcs | classical · western · humanistic |

> Worked examples ship in `examples_*.json`. Open any exported `.html` and press
> **F** to present; **← →** to walk the tour; **EN / 中** to switch worlds.

## Project layout

```
backend/
  build.py            web mode — research a subject
  build_corpus.py     corpus mode — read your own documents
  pipeline.py         the six stages
  schemas.py          structured-output models
  graph.py            the bilingual graph (the contract everything fills)
  clients.py          two-model wrappers, search, sub-agents
  planner.py          depth auto-assessment + relevance scheduler
  theme.py            the design-taste engine
  corpus.py           document reading + chunking
  export_html.py      single-file presentation export
  evaluation/         precision/recall harness + gold set
examples_*.json       worked graphs (Daodejing, Stoicism)
```

## Acknowledgements

Maia stands on three ideas:

- The engineering of Anthropic's [knowledge-graph cookbook](https://github.com/anthropics/claude-cookbooks)
  — structured extraction, description-based resolution, an evaluation loop.
- **Wittgenstein**, for *the limits of language are the limits of the world* — why
  the two language graphs are built apart.
- **Steve Jobs**, for *ultimately it comes down to taste* — why the design adapts to
  the subject instead of defaulting to one look.

And the spirit of [Understand-Anything](https://github.com/Lum1104/Understand-Anything):
**graphs that teach > graphs that impress.** Maia carries that conviction from code
into ideas.

## License

MIT — do anything, just keep the notice.

<div align="center">
<sub>Built to be read, walked, and understood — not just looked at.</sub>
</div>
