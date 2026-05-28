---
name: maia:view
description: Export and open a Maia knowledge graph as a self-contained HTML file
argument-hint: "[graph.json path] [--out output.html]"
---

# /maia:view

Export a Maia graph JSON to a self-contained HTML file and open it in the browser.

## Step 1 — Locate the plugin root

```bash
SKILL_REAL=$(realpath ~/.agents/skills/maia:view 2>/dev/null || readlink -f ~/.agents/skills/maia:view 2>/dev/null || echo "")
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

## Step 2 — Resolve graph and output paths

From `$ARGUMENTS`:
- If a `.json` path is given, use it as `GRAPH`
- Otherwise, use the most recently modified `*.json` in `$PLUGIN_ROOT/output/` that is not a `theme.json`:
  ```bash
  GRAPH=$(ls -t "$PLUGIN_ROOT/output/"*.json 2>/dev/null | grep -v theme.json | head -1)
  ```

- If `--out <path>` is given, use that as `HTML_OUT`
- Otherwise derive from the graph filename: `$PLUGIN_ROOT/output/<stem>.html`

If no graph is found, tell the user:
> No graph found. Run `/maia:build <topic>` first.

Also locate the matching `theme.json`:
```bash
THEME_DIR=$(dirname "$GRAPH")
THEME="$THEME_DIR/theme.json"
[ -f "$THEME" ] || THEME=""
```

## Step 3 — Activate venv

```bash
source "$PLUGIN_ROOT/backend/.venv/bin/activate"
```

If the venv doesn't exist, tell the user to run `/maia:build` first (it sets up the environment).

## Step 4 — Export

```bash
cd "$PLUGIN_ROOT/backend"
if [ -n "$THEME" ]; then
  python export_html.py "$GRAPH" "$THEME" "$HTML_OUT"
else
  python export_html.py "$GRAPH" "$HTML_OUT"
fi
```

## Step 5 — Open

```bash
open "$HTML_OUT"
```

Report:
> Opened: `<HTML_OUT>`
> **F** — fullscreen · **← →** — tour · **EN / 中** — switch language
