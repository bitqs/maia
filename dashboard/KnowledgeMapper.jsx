import React, { useState, useMemo, useRef, useEffect } from "react";

// ── Knowledge Mapper dashboard ───────────────────────────────────────────
// Reads the graph.json produced by the backend pipeline. Drop your file's
// contents into SAMPLE below, or fetch() it. Force-directed layout is done
// by hand (no heavy deps) so this runs as a single self-contained artifact.

const SAMPLE = {
  expert: "Judea Pearl",
  domain: "Causal Inference",
  nodes: [
    { id: "scm", name: "Structural Causal Models", type: "theory", difficulty: "foundational", summary: "A framework representing causal relationships as functional equations among variables.", sources: ["#"] },
    { id: "do", name: "Do-Calculus", type: "method", difficulty: "intermediate", summary: "A set of rules for transforming expressions involving interventions into observational quantities.", sources: ["#"] },
    { id: "cf", name: "Counterfactuals", type: "concept", difficulty: "advanced", summary: "Statements about what would have happened under alternative, unrealized conditions.", sources: ["#"] },
    { id: "ladder", name: "Ladder of Causation", type: "theory", difficulty: "foundational", summary: "Three rungs of reasoning: association, intervention, counterfactuals.", sources: ["#"] },
    { id: "dag", name: "Causal DAGs", type: "tool", difficulty: "foundational", summary: "Directed acyclic graphs encoding causal assumptions among variables.", sources: ["#"] },
    { id: "backdoor", name: "Backdoor Criterion", type: "method", difficulty: "intermediate", summary: "A graphical test for which variables to adjust for to estimate causal effects.", sources: ["#"] },
  ],
  edges: [
    { source: "do", target: "scm", relation: "depends_on" },
    { source: "cf", target: "scm", relation: "part_of" },
    { source: "backdoor", target: "dag", relation: "depends_on" },
    { source: "do", target: "dag", relation: "applies" },
    { source: "ladder", target: "cf", relation: "leads_to" },
    { source: "ladder", target: "do", relation: "leads_to" },
  ],
  meta: { foundational: ["scm", "dag", "ladder"], tour: ["ladder", "dag", "scm", "backdoor", "do", "cf"] },
};

const DIFF_COLOR = { foundational: "#d97706", intermediate: "#0891b2", advanced: "#be185d" };
const REL_LABEL = { depends_on: "depends on", part_of: "part of", contrasts_with: "contrasts", leads_to: "leads to", applies: "applies", subtype_of: "subtype of" };

function useForceLayout(nodes, edges, w, h) {
  const [pos, setPos] = useState(() => {
    const m = {};
    nodes.forEach((n, i) => {
      const a = (i / nodes.length) * Math.PI * 2;
      m[n.id] = { x: w / 2 + Math.cos(a) * 160, y: h / 2 + Math.sin(a) * 160, vx: 0, vy: 0 };
    });
    return m;
  });
  const raf = useRef();
  useEffect(() => {
    let ticks = 0;
    const step = () => {
      setPos((prev) => {
        const p = JSON.parse(JSON.stringify(prev));
        const ids = nodes.map((n) => n.id);
        for (let i = 0; i < ids.length; i++)
          for (let j = i + 1; j < ids.length; j++) {
            const a = p[ids[i]], b = p[ids[j]];
            let dx = a.x - b.x, dy = a.y - b.y;
            let d = Math.sqrt(dx * dx + dy * dy) || 1;
            const f = 4200 / (d * d);
            a.vx += (dx / d) * f; a.vy += (dy / d) * f;
            b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
          }
        edges.forEach((e) => {
          const a = p[e.source], b = p[e.target];
          if (!a || !b) return;
          let dx = b.x - a.x, dy = b.y - a.y;
          let d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = (d - 120) * 0.01;
          a.vx += (dx / d) * f; a.vy += (dy / d) * f;
          b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
        });
        ids.forEach((id) => {
          const n = p[id];
          n.vx += (w / 2 - n.x) * 0.002;
          n.vy += (h / 2 - n.y) * 0.002;
          n.x += (n.vx *= 0.85); n.y += (n.vy *= 0.85);
          n.x = Math.max(40, Math.min(w - 40, n.x));
          n.y = Math.max(40, Math.min(h - 40, n.y));
        });
        return p;
      });
      if (++ticks < 220) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [nodes, edges, w, h]);
  return pos;
}

export default function KnowledgeMapper() {
  const data = SAMPLE;
  const W = 640, H = 460;
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [tourStep, setTourStep] = useState(-1);
  const pos = useForceLayout(data.nodes, data.edges, W, H);

  const match = useMemo(() => {
    if (!query) return null;
    const q = query.toLowerCase();
    return new Set(data.nodes.filter((n) =>
      n.name.toLowerCase().includes(q) || (n.summary || "").toLowerCase().includes(q)
    ).map((n) => n.id));
  }, [query, data.nodes]);

  const tour = data.meta?.tour || [];
  const tourActive = tourStep >= 0 ? tour[tourStep] : null;
  const nodeById = (id) => data.nodes.find((n) => n.id === id);
  const active = selected || (tourActive ? nodeById(tourActive) : null);

  return (
    <div style={{ fontFamily: "'Georgia', serif", background: "#faf8f3", color: "#1c1917", minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "20px 24px", borderBottom: "2px solid #1c1917" }}>
        <div style={{ fontSize: 12, letterSpacing: 3, textTransform: "uppercase", color: "#78716c" }}>Knowledge Map</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 30, fontWeight: 400 }}>{data.expert}</h1>
        <div style={{ fontSize: 15, fontStyle: "italic", color: "#57534e" }}>{data.domain}</div>
      </header>

      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {/* graph */}
        <div style={{ position: "relative", flex: "1 1 640px" }}>
          <input
            value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Search concepts…"
            style={{ position: "absolute", top: 12, left: 12, zIndex: 5, padding: "7px 12px", border: "1px solid #1c1917", background: "#fffef9", fontFamily: "inherit", fontSize: 13, width: 180 }}
          />
          <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
            {data.edges.map((e, i) => {
              const a = pos[e.source], b = pos[e.target];
              if (!a || !b) return null;
              return (
                <g key={i}>
                  <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#d6d3d1" strokeWidth={1.2} />
                  <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2} fontSize={8} fill="#a8a29e" fontFamily="sans-serif" textAnchor="middle">{REL_LABEL[e.relation]}</text>
                </g>
              );
            })}
            {data.nodes.map((n) => {
              const p = pos[n.id]; if (!p) return null;
              const dim = match && !match.has(n.id);
              const isActive = active?.id === n.id;
              const r = (data.meta?.foundational || []).includes(n.id) ? 11 : 8;
              return (
                <g key={n.id} transform={`translate(${p.x},${p.y})`} style={{ cursor: "pointer", opacity: dim ? 0.2 : 1 }} onClick={() => { setSelected(n); setTourStep(-1); }}>
                  <circle r={isActive ? r + 4 : r} fill={DIFF_COLOR[n.difficulty] || "#57534e"} stroke={isActive ? "#1c1917" : "#fffef9"} strokeWidth={isActive ? 3 : 2} />
                  <text y={r + 13} fontSize={10} textAnchor="middle" fill="#1c1917" fontFamily="sans-serif">{n.name}</text>
                </g>
              );
            })}
          </svg>
          <div style={{ position: "absolute", bottom: 10, left: 12, fontSize: 11, fontFamily: "sans-serif", color: "#78716c" }}>
            {Object.entries(DIFF_COLOR).map(([k, c]) => (
              <span key={k} style={{ marginRight: 12 }}><span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 9, background: c, marginRight: 4 }} />{k}</span>
            ))}
          </div>
        </div>

        {/* side panel */}
        <aside style={{ flex: "1 1 300px", borderLeft: "1px solid #d6d3d1", padding: 20, minWidth: 280 }}>
          {/* tour */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, letterSpacing: 2, textTransform: "uppercase", color: "#78716c", marginBottom: 8 }}>Guided Tour</div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
              <button onClick={() => { setTourStep((s) => Math.max(0, s - 1)); setSelected(null); }} disabled={tourStep <= 0} style={btn}>‹</button>
              <button onClick={() => { setTourStep((s) => (s < 0 ? 0 : Math.min(tour.length - 1, s + 1))); setSelected(null); }} style={btn}>{tourStep < 0 ? "Start tour" : "Next ›"}</button>
              {tourStep >= 0 && <span style={{ fontSize: 12, color: "#78716c" }}>{tourStep + 1} / {tour.length}</span>}
            </div>
          </div>

          {active ? (
            <div>
              <div style={{ fontSize: 11, fontFamily: "sans-serif", color: DIFF_COLOR[active.difficulty], textTransform: "uppercase", letterSpacing: 1 }}>{active.type} · {active.difficulty}</div>
              <h2 style={{ margin: "4px 0 8px", fontSize: 22, fontWeight: 400 }}>{active.name}</h2>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: "#44403c" }}>{active.summary}</p>
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 11, color: "#78716c", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Connections</div>
                {data.edges.filter((e) => e.source === active.id || e.target === active.id).map((e, i) => {
                  const other = e.source === active.id ? e.target : e.source;
                  return <div key={i} style={{ fontSize: 13, padding: "3px 0", color: "#57534e" }}>{REL_LABEL[e.relation]} → <b>{nodeById(other)?.name}</b></div>;
                })}
              </div>
              {active.sources?.length > 0 && (
                <div style={{ marginTop: 12, fontSize: 12 }}>
                  <span style={{ color: "#78716c" }}>Sources: </span>
                  {active.sources.map((s, i) => <a key={i} href={s} style={{ color: "#0891b2", marginRight: 8 }}>[{i + 1}]</a>)}
                </div>
              )}
            </div>
          ) : (
            <p style={{ fontSize: 14, color: "#78716c", fontStyle: "italic" }}>Click a node or start the guided tour to explore the system.</p>
          )}
        </aside>
      </div>
    </div>
  );
}

const btn = { padding: "6px 12px", border: "1px solid #1c1917", background: "#fffef9", fontFamily: "Georgia, serif", fontSize: 13, cursor: "pointer" };
