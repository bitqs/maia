---
name: maia:view
description: Export and open a Maia knowledge graph as a self-contained HTML file
argument-hint: "[graph.json path] [--out output.html]"
---

# /maia:view

Export a Maia graph JSON to a self-contained HTML file and open it in the browser.

## Step 1 — Locate the plugin root

```bash
PLUGIN_ROOT="$HOME/.claude/plugins/cache/maia/maia/1.0.0"
[ -f "$PLUGIN_ROOT/.claude-plugin/plugin.json" ] || { echo "Plugin root not found. Run /maia:build first."; exit 1; }
BACKEND="$PLUGIN_ROOT/backend"
OUTPUT="$PLUGIN_ROOT/output"
```

## Step 2 — Resolve graph and output paths

From `$ARGUMENTS`:
- If a `.json` path is given, use it as `GRAPH`
- Otherwise, use the most recently modified `*.json` in `$OUTPUT/` that is not `theme.json`:
  ```bash
  GRAPH=$(ls -t "$OUTPUT/"*.json 2>/dev/null | grep -v theme.json | head -1)
  ```

- If `--out <path>` is given, use that as `HTML_OUT`
- Otherwise derive from the graph filename: `$OUTPUT/<stem>.html`

If no graph is found, tell the user:
> No graph found. Run `/maia:build <topic>` first.

## Step 3 — Check venv

```bash
VENV="$BACKEND/.venv"
[ -f "$VENV/bin/python" ] || { echo "Environment not set up. Run /maia:build first."; exit 1; }
```

## Step 4 — Export

```bash
cd "$BACKEND" && .venv/bin/python export_html.py "$GRAPH" "$HTML_OUT"
```

## Step 5 — Open

```bash
open "$HTML_OUT"
```

Report:
> Opened: `<HTML_OUT>`
> **F** — fullscreen · **← →** — tour · **EN / 中** — switch language
