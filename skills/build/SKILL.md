---
name: maia:build
description: Build an interactive bilingual knowledge graph from a subject (web research) or your own documents
argument-hint: "<topic> | --corpus <paths...> [--lang en|zh|both] [--depth <n>]"
---

# /maia:build

Build a Maia knowledge graph. Supports two modes:

- **Web mode** — Maia researches a topic or thinker on the web
- **Corpus mode** — Maia reads your own documents (`.md`, `.txt`, `.pdf`, `.docx`)

## Step 1 — Parse arguments

From `$ARGUMENTS`, extract:

- `--corpus <paths...>` — one or more file/directory paths. If present, use corpus mode.
- `--lang <value>` — `en`, `zh`, or `both` (default: `en`)
- `--depth <n>` — integer depth override (optional; Maia auto-decides if omitted)
- `--title <text>` — graph title for corpus mode (optional)
- Everything else is the **topic** (web mode), e.g. `Stoicism`, `Laozi Daodejing`, `causal inference`

If no arguments are given, ask the user:
> What would you like to map? Give a topic (e.g. "Stoicism") or pass `--corpus <paths>` to map your own documents.

## Step 2 — Locate the plugin root

The plugin lives at the path of this skill's parent directory (`skills/build/` → plugin root two levels up).

```bash
SKILL_REAL=$(realpath ~/.agents/skills/maia:build 2>/dev/null || readlink -f ~/.agents/skills/maia:build 2>/dev/null || echo "")
PLUGIN_ROOT=""
for candidate in \
  "/Users/$USER/.claude/plugins/cache/maia/maia/1.0.0" \
  "$HOME/.maia-plugin" \
  "$([ -n "$SKILL_REAL" ] && cd "$SKILL_REAL/../.." 2>/dev/null && pwd || echo "")"; do
  if [ -n "$candidate" ] && [ -f "$candidate/.claude-plugin/plugin.json" ]; then
    PLUGIN_ROOT="$candidate"
    break
  fi
done
```

If `PLUGIN_ROOT` is empty, report:
> Cannot locate the Maia plugin root. Ensure Maia is installed correctly.

## Step 3 — Set up the Python environment

```bash
BACKEND="$PLUGIN_ROOT/backend"
VENV="$BACKEND/.venv"
```

If `$VENV/bin/python` does not exist:
```bash
cd "$BACKEND" && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

Otherwise just activate:
```bash
source "$VENV/bin/activate"
```

## Step 4 — Check ANTHROPIC_API_KEY

If `ANTHROPIC_API_KEY` is not set, tell the user:
> Set your API key first: `export ANTHROPIC_API_KEY=sk-...`

Then stop.

## Step 5 — Run the build

Create `$PLUGIN_ROOT/output/` if it does not exist.

### Web mode

```bash
cd "$BACKEND" && source .venv/bin/activate
python build.py --expert "<topic>" --domain "core concepts" --lang <lang>
```

If `--depth` was given, append `--depth <n>`.

If `--lang both`, run twice: once with `--lang en`, once with `--lang zh`.

### Corpus mode

```bash
cd "$BACKEND" && source .venv/bin/activate
python build_corpus.py --paths <paths...> [--title "<title>"] --lang <lang>
```

If `--lang both`, run twice.

## Step 6 — Export to HTML

After a successful build, export each produced `graph.json`:

```bash
cd "$BACKEND" && source .venv/bin/activate
GRAPH="$PLUGIN_ROOT/output/graph.json"
THEME="$PLUGIN_ROOT/output/theme.json"
OUT="$PLUGIN_ROOT/output/<slug>.html"
python export_html.py "$GRAPH" "$THEME" "$OUT"
```

Where `<slug>` is a filesystem-safe version of the topic or title (lowercase, spaces→hyphens).

## Step 7 — Open

```bash
open "$OUT"
```

Report the output path to the user:
> Graph built: `<OUT>`
> Press **F** to present · **← →** to walk the tour · **EN / 中** to switch language

---

## Error handling

- If `build.py` / `build_corpus.py` exits non-zero, print the last 30 lines of output and stop.
- If `export_html.py` fails, still report the raw `graph.json` path — the graph exists, only the export failed.
