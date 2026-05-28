# /map-knowledge — Claude Code command

This wraps the pipeline as a Claude Code slash command so it works like
Understand-Anything's `/understand`.

> NOTE: Claude Code's plugin/marketplace manifest format changes often.
> Before publishing, check the current spec at docs.claude.com and adjust
> the command-registration format below to match. The *logic* (call build.py,
> then open the dashboard) stays the same regardless of the wrapper format.

## What the command does

1. Ask the user (or read args) for: expert, domain, optional seed concepts.
2. Run the backend pipeline:
   ```bash
   python backend/build.py \
     --expert "$EXPERT" --domain "$DOMAIN" --seeds "$SEEDS" \
     --max-depth 2 --max-nodes 50 --out output/graph.json
   ```
3. Inject `output/graph.json` into the dashboard and open it locally.

## Example invocation

```
/map-knowledge expert="Judea Pearl" domain="causal inference" \
  seeds="do-calculus, structural causal models, counterfactuals"
```

## Wiring the dashboard to real data

The dashboard ships with a `SAMPLE` constant. To load real output, replace it
with a fetch on mount:

```jsx
const [data, setData] = useState(null);
useEffect(() => { fetch("/graph.json").then(r => r.json()).then(setData); }, []);
if (!data) return <div>Loading graph…</div>;
```

Serve the folder with any static server (e.g. `python -m http.server`) and put
`graph.json` alongside the built dashboard.
