---
name: maia:build
description: Build an interactive bilingual knowledge graph from a subject (web research) or your own documents
argument-hint: "<topic> | --corpus <paths...> [--lang en|zh|both] [--depth <n>]"
---

# /maia:build

Build a Maia knowledge graph. Two modes: web research or your own documents.
**No API key required** — you ARE the model. Python only validates and exports.

## Step 1 — Parse arguments

From `$ARGUMENTS`:
- `--corpus <paths...>` — one or more file/directory paths → corpus mode
- `--lang en|zh|both` — graph language(s), default `en`
- `--depth <n>` — 1 ≈ 25 nodes, 2 ≈ 50, 3 ≈ 80 (auto-decide if omitted)
- `--title <text>` — graph title for corpus mode (optional)
- Everything else = **topic** (web mode)

If no arguments given, ask:
> What would you like to map? Give a topic (e.g. "Wittgenstein") or pass `--corpus <paths>` to map your own documents.

## Step 2 — Locate plugin root

```bash
PLUGIN_ROOT="$HOME/.claude/plugins/cache/maia/maia/1.0.0"
[ -f "$PLUGIN_ROOT/.claude-plugin/plugin.json" ] || { echo "Plugin root not found"; exit 1; }
BACKEND="$PLUGIN_ROOT/backend"
OUTPUT="$PLUGIN_ROOT/output"
mkdir -p "$OUTPUT"
```

## Step 3 — Python environment

```bash
VENV="$BACKEND/.venv"
[ -f "$VENV/bin/python" ] || (cd "$BACKEND" && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
```

---

## Step 4 — Web mode: research and build

**You are the research engine.** Use your knowledge + WebSearch. No Python LLM calls needed.

### 4a Research

Do 3-5 targeted web searches:

1. `"<topic>" core concepts overview` — broad orientation, identify pillar ideas
2. `"<topic>" <most important concept>` — depth on the top concept
3. `"<topic>" 核心概念 简介` — Chinese-language sources for bilingual content
4. (optional) `"<topic>" <second important concept>` — if more depth needed

Skim 2-3 authoritative pages with WebFetch. Collect real URLs for `sources` fields.

### 4b Assemble graph.json

Build the complete graph structure from your research + knowledge. Schema:

```json
{
  "schema": "bilingual-v2",
  "expert": {"en": "Topic Name", "zh": "主题中文名"},
  "domain": {"en": "core concepts", "zh": "核心概念"},
  "nodes": [ ...see node schema below... ],
  "edges": [ ...see edge schema below... ],
  "meta": {
    "foundational": ["id1", "id2"],
    "tour": ["id1", "id2", "id3", "...ordered learning path..."]
  },
  "lang_default": "<lang>"
}
```

**Node schema:**
```json
{
  "id": "language-game",
  "name": {"en": "Language-Game", "zh": "语言游戏"},
  "type": "concept",
  "summary": {"en": "One clear paragraph.", "zh": "一段话中文摘要。"},
  "tags": [{"en": "core", "zh": "核心"}],
  "difficulty": "foundational",
  "relevance": 0.95,
  "sources": ["https://example.com/..."],
  "depth": 0,
  "aliases": [],
  "explored_by": "main",
  "profile": {
    "what":     {"en": "2-3 real sentences on what this IS.", "zh": "2-3句说明这是什么。"},
    "why":      {"en": "Why it matters in this body of knowledge.", "zh": "在此知识体系中为何重要。"},
    "position": {"en": "Its structural place: what it grounds, what depends on it.", "zh": "结构位置：它奠定了什么，又依赖什么。"},
    "quote":    {"en": "Exact canonical quotation OR concrete example.", "zh": "原文引用或具体示例。"},
    "quote_source": "Work title, §section or chapter"
  }
}
```

**Edge schema:**
```json
{
  "source": "source-node-id",
  "target": "target-node-id",
  "relation": {"en": "depends_on", "zh": "依赖于"},
  "evidence": "brief phrase from source"
}
```

**ID rules:**
- `id` = EN name, lowercase, spaces→hyphens, strip non-alphanumeric (e.g. `"language-game"`)
- If no EN name exists, use pinyin slug

**`difficulty` values:** `foundational` / `intermediate` / `advanced`

**`depth`:** 0 = seed concept, 1 = first expansion, 2 = second expansion

**Valid relation types with Chinese labels:**

| en | zh |
|---|---|
| `depends_on` | `依赖于` |
| `part_of` | `属于` |
| `contrasts_with` | `对立于` |
| `leads_to` | `导向` |
| `applies` | `应用于` |
| `subtype_of` | `子类型` |

**Quality targets:**
- 25-50 nodes for most topics; 15-25 for tightly bounded subjects
- Every node: non-empty `profile.what` in both languages
- `meta.tour`: ordered from bedrock foundations → applications (the learning path)
- `profile.quote`: real quotations only — if none available, use a concrete canonical example
- Prefer depth over breadth: fewer nodes with richer profiles > many thin nodes

### 4c Write graph.json

Use the **Write tool** to save the assembled JSON to `$OUTPUT/graph.json`.

---

## Step 5 — Corpus mode

If `--corpus` was given:

1. Read each file using the **Read tool** (or list directories with Bash)
2. Extract concepts and relationships — same JSON schema as above
3. `sources` field = filename with chunk reference (e.g. `"notes.md#3"`)
4. Use `--title` as `expert.en/zh`; infer Chinese title if not given
5. Write to `$OUTPUT/graph.json`, then continue at Step 6

---

## Step 6 — Validate and normalize

```bash
cd "$BACKEND" && .venv/bin/python validate.py "$OUTPUT/graph.json"
```

This normalizes node IDs, removes broken edges, and fills missing fields. If it fails, inspect the error and fix `graph.json` before continuing.

---

## Step 7 — Export to HTML

```bash
SLUG=$(python3 -c "import re,sys; s=sys.argv[1].lower(); s=re.sub(r'[^a-z0-9一-鿿]+','-',s).strip('-'); print(s)" "<topic>")
cd "$BACKEND" && .venv/bin/python export_html.py "$OUTPUT/graph.json" "$OUTPUT/${SLUG}.html"
```

---

## Step 8 — Open

```bash
open "$OUTPUT/${SLUG}.html"
```

Report:
> Graph built: `<full path to .html>`
> Press **F** to present · **← →** to walk the tour · **EN / 中** to switch language

---

## Error handling

- `validate.py` fails → inspect error, patch `graph.json`, re-run validate
- `export_html.py` fails → report raw `graph.json` path; graph exists even without HTML
- If `--lang both`: build one graph with bilingual content (both `en` and `zh` filled in every node); set `lang_default` to `en`
