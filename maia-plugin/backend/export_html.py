"""
export_html.py — bundle a graph.json + ThemeSpec into ONE self-contained .html.

v5 — DEPTH + LEFT/RIGHT LAYOUT:
  * Two-column layout (Understand-Anything's node-inspector paradigm): graph on
    the left (~62%), a persistent inspector panel on the right (~38%).
  * The inspector shows the NODE ARCHIVE: what it is / why it matters / its place
    in the system / a key quotation — not a one-line card. This is the depth
    upgrade that closes the gap with Understand-Anything.
  * Fullscreen-adaptive, presentation-legible typography, EN/中 toggle, guided
    tour with the inspector following along, search, keyboard nav.

Double-click to open: no server, no build, no network.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path


DEFAULT_THEME = {
    "name": "editorial",
    "bg_css": "#ebe6da",
    "ink": "#2a1f14",
    "accent": "#9a7a5a",
    "node_core": "#c8a06a",
    "node_edge": "#9a7a5a",
    "text_on_bg": "#2a1f14",
    "font_display": "Georgia, 'Songti SC', serif",
    "font_body": "Georgia, 'Songti SC', serif",
    "letterspacing": "0",
    "layout": "radial",
    "edge_style": "curved",
    "node_shape": "circle",
    "centrality_by": "solidity",
    "rationale_en": "",
    "rationale_zh": "",
}
FONT_MAP = {
    "var(--font-serif)": "Georgia, 'Songti SC', 'Noto Serif', serif",
    "var(--font-sans)": "-apple-system, 'Helvetica Neue', 'PingFang SC', Arial, sans-serif",
    "var(--font-mono)": "'SF Mono', 'Cascadia Code', Menlo, 'Courier New', monospace",
}


def resolve_font(f):
    return FONT_MAP.get(f, f)


def build_html(graph, theme, title="Knowledge Map"):
    th = {**DEFAULT_THEME, **(theme or {})}
    th["font_display"] = resolve_font(th["font_display"])
    th["font_body"] = resolve_font(th["font_body"])
    payload = json.dumps({"graph": graph, "theme": th}, ensure_ascii=False).replace(
        "</", "<\\/"
    )
    return TEMPLATE.replace("__TITLE__", title).replace("__PAYLOAD__", payload)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; width: 100%; overflow: hidden; }
  body { background: #ebe6da; font-family: var(--fb); }
  .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }

  #wrap { position: relative; width: 100vw; height: 100vh; display: flex; flex-direction: column; }
  #bgfill { position: absolute; inset: 0; z-index: 0; }

  header { position: relative; z-index: 2; padding: clamp(16px,2.6vh,34px) clamp(24px,3.5vw,60px) 0; pointer-events: none; }
  .eyebrow { font-size: clamp(11px,0.95vw,14px); letter-spacing: 0.3em; text-transform: uppercase; opacity: 0.5; }
  h1 { font-size: clamp(24px,3vw,48px); font-weight: 400; line-height: 1.05; margin-top: 0.2em; font-family: var(--fd); }
  .sub { font-size: clamp(13px,1.4vw,20px); font-style: italic; opacity: 0.62; margin-top: 0.12em; font-family: var(--fd); }

  .controls { position: relative; z-index: 4; display: flex; flex-wrap: wrap; align-items: center; gap: clamp(8px,1vw,14px); padding: clamp(10px,1.4vh,20px) clamp(24px,3.5vw,60px) 0; }
  .seg { display: inline-flex; border: 0.5px solid; border-radius: 999px; overflow: hidden; }
  .seg button { border: none; border-radius: 0; padding: 4px 17px; background: transparent; cursor: pointer; font-size: clamp(13px,1vw,16px); font-family: var(--fb); }
  .pill { width: auto; padding: 4px 17px; border-radius: 999px; border: 0.5px solid; background: transparent; cursor: pointer; font-size: clamp(13px,1vw,16px); font-family: var(--fb); }
  .pill:hover { background: rgba(255,255,255,0.05); }
  .pos { font-size: clamp(12px,0.95vw,15px); opacity: 0.5; }
  input[type=text] { padding: 5px 14px; border: 0.5px solid; border-radius: 999px; background: transparent; font-size: clamp(13px,1vw,15px); width: clamp(110px,11vw,170px); font-family: var(--fb); }

  /* the two-column body: graph left, inspector right */
  #body { position: relative; z-index: 1; flex: 1 1 auto; min-height: 0; display: flex; }
  #graphbox { position: relative; flex: 1 1 62%; min-width: 0; }
  svg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  #legend { position: absolute; bottom: clamp(10px,1.4vh,18px); left: clamp(24px,3.5vw,60px); font-size: clamp(11px,0.9vw,13px); opacity: 0.5; z-index: 2; pointer-events: none; }

  #inspector {
    flex: 0 0 clamp(300px, 36%, 480px);
    border-left: 0.5px solid;
    padding: clamp(18px,2.6vh,34px) clamp(20px,2.2vw,36px);
    overflow-y: auto; z-index: 3;
  }
  #inspector .kicker { font-size: clamp(11px,0.9vw,13px); letter-spacing: 0.18em; text-transform: uppercase; opacity: 0.55; }
  #inspector .nm { font-size: clamp(24px,2.4vw,38px); line-height: 1.08; margin: 0.2em 0 0.1em; font-family: var(--fd); }
  #inspector .alt { font-size: clamp(15px,1.4vw,20px); opacity: 0.55; font-family: var(--fd); }
  .archive { margin-top: clamp(14px,2vh,24px); }
  .seg-label { font-size: clamp(11px,0.9vw,13px); letter-spacing: 0.14em; text-transform: uppercase; opacity: 0.5; margin-bottom: 0.3em; }
  .seg-body { font-size: clamp(14px,1.25vw,18px); line-height: 1.72; opacity: 0.9; margin-bottom: clamp(12px,1.8vh,22px); }
  .quote { border-left: 2px solid; padding-left: 14px; margin: clamp(10px,1.6vh,20px) 0; }
  .quote .q { font-size: clamp(16px,1.5vw,22px); line-height: 1.6; font-style: italic; font-family: var(--fd); }
  .quote .qs { font-size: clamp(12px,1vw,14px); opacity: 0.55; margin-top: 0.4em; }
  .rels { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: clamp(8px,1.2vh,16px); }
  .rel { font-size: clamp(12.5px,1.1vw,15px); opacity: 0.72; cursor: pointer; }
  .rel:hover { opacity: 1; text-decoration: underline; }
  .hint { font-size: clamp(14px,1.3vw,18px); line-height: 1.7; opacity: 0.65; font-style: italic; font-family: var(--fd); }

  footer { position: relative; z-index: 2; padding: 0 clamp(24px,3.5vw,60px) clamp(8px,1.2vh,16px); font-size: clamp(11px,0.9vw,13px); opacity: 0.4; font-style: italic; font-family: var(--fd); }

  /* present mode */
  body.present .eyebrow, body.present .controls, body.present footer { display: none; }
  #presentBtn { position: absolute; top: clamp(16px,2.6vh,34px); right: clamp(24px,3.5vw,60px); z-index: 5; }

  /* narrow screens: stack */
  @media (max-width: 720px) {
    #body { flex-direction: column; }
    #graphbox { flex: 1 1 55%; }
    #inspector { flex: 1 1 45%; border-left: none; border-top: 0.5px solid; }
  }
</style>
</head>
<body>
<div id="wrap">
  <div id="bgfill"></div>
  <button id="presentBtn" class="pill"></button>
  <h2 class="sr-only">Interactive bilingual knowledge graph with a deep node inspector (what / why / position / key quotation), guided tour, and fullscreen presentation.</h2>
  <header>
    <div class="eyebrow">Knowledge Map</div>
    <h1 id="h-expert"></h1>
    <div class="sub" id="h-domain"></div>
  </header>
  <div class="controls" id="controls"></div>
  <div id="body">
    <div id="graphbox">
      <svg id="svg" role="img" preserveAspectRatio="xMidYMid meet">
        <title>Concept graph</title><desc id="svg-desc"></desc>
        <defs id="defs"></defs>
        <g id="edges" fill="none"></g>
        <g id="elabels"></g>
        <g id="nodes"></g>
      </svg>
      <div id="legend"></div>
    </div>
    <aside id="inspector" aria-live="polite"></aside>
  </div>
  <footer id="rationale"></footer>
</div>

<script>
const DATA = __PAYLOAD__;
const G = DATA.graph, TH = DATA.theme;
const NODES = G.nodes, EDGES = G.edges;
const META = G.meta || {tour: [], foundational: []};
const byId = {}; NODES.forEach(n => byId[n.id] = n);
const FOUND = new Set(META.foundational || []);
let lang = (G.lang_default === "zh") ? "zh" : "en";
let cur = null, tourIdx = -1;

document.documentElement.style.setProperty("--fd", TH.font_display);
document.documentElement.style.setProperty("--fb", TH.font_body);
document.body.style.color = TH.text_on_bg;
document.getElementById("bgfill").style.background = TH.bg_css;
document.getElementById("inspector").style.borderColor = TH.accent + "33";

const NS="http://www.w3.org/2000/svg";
const svg = document.getElementById("svg");
const eg = document.getElementById("edges"), ng = document.getElementById("nodes");
function el(t,a){ const e=document.createElementNS(NS,t); for(const k in a) e.setAttribute(k,a[k]); return e; }
function nm(n,l){ const v=n.name||{}; return (l==="zh"?v.zh:v.en)||v.en||v.zh||n.id; }
function sm(n,l){ const v=n.summary||{}; return (l==="zh"?v.zh:v.en)||v.en||v.zh||""; }
function rel(e,l){ const v=e.relation||{}; return (l==="zh"?v.zh:v.en)||v.en||v.zh||""; }
function relevance(n){ return (typeof n.relevance==="number")?n.relevance:0.7; }
function pf(n,part,l){ const p=(n.profile||{})[part]; if(!p) return ""; return (l==="zh"?p.zh:p.en)||p.en||p.zh||""; }

let W=1200,H=700,pos={};
function computeLayout(){
  const box=document.getElementById("graphbox").getBoundingClientRect();
  W=Math.max(420,box.width); H=Math.max(360,box.height);
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
  const CX=W/2, CY=H/2, spread=Math.min(W,H)*0.44;
  const root=(META.tour&&META.tour[0])||(META.foundational&&META.foundational[0])||NODES[0].id;
  pos={};
  NODES.forEach((n,i)=>{const a=i/NODES.length*6.283;const r=spread*(0.35+(1-relevance(n))*0.65);pos[n.id]={x:CX+Math.cos(a)*r,y:CY+Math.sin(a)*r,vx:0,vy:0};});
  if(TH.layout==="grid"){
    const order=[...NODES].sort((a,b)=>relevance(b)-relevance(a));
    const cols=Math.max(3,Math.round(Math.sqrt(NODES.length)*1.2));
    const cw=W/(cols+1),rh=Math.min(H/(Math.ceil(NODES.length/cols)+1),120);
    order.forEach((n,i)=>{const r=Math.floor(i/cols),c=i%cols;pos[n.id]={x:cw*(c+1)+(r%2)*20,y:rh*(r+1.2),vx:0,vy:0};});
    drawAll();return;
  }
  pos[root]={x:CX,y:CY,vx:0,vy:0};
  const ids=NODES.map(n=>n.id),repel=spread*spread*1.0,LL=spread*0.78;
  for(let it=0;it<480;it++){
    for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){const a=pos[ids[i]],b=pos[ids[j]];let dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1,f=repel/(d*d);a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
    EDGES.forEach(e=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return;let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-LL)*0.013;a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;});
    ids.forEach(k=>{const n=pos[k],tr=spread*(0.28+(1-relevance(byId[k]))*0.72);let dx=n.x-CX,dy=n.y-CY,d=Math.hypot(dx,dy)||1;n.vx+=dx/d*(tr-d)*0.02;n.vy+=dy/d*(tr-d)*0.02;if(k===root){n.x=CX;n.y=CY;return;}n.x+=(n.vx*=0.8);n.y+=(n.vy*=0.8);const m=Math.min(W,H)*0.07,mb=Math.min(W,H)*0.14;n.x=Math.max(m,Math.min(W-m,n.x));n.y=Math.max(m,Math.min(H-mb,n.y));});
  }
  drawAll();
}

let edgeEls=[],nodeEls={};
function drawAll(){
  eg.innerHTML="";ng.innerHTML="";edgeEls=[];nodeEls={};
  const base=Math.min(W,H),coreR=base*0.072,periR=base*0.022;
  EDGES.forEach(e=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return;let d;
    if(TH.edge_style==="straight"||TH.edge_style==="elbow"){d=`M${a.x},${a.y} L${b.x},${b.y}`;}
    else{const mx=(a.x+b.x)/2,my=(a.y+b.y)/2,dx=b.x-a.x,dy=b.y-a.y,h=Math.hypot(dx,dy)||1,k=(TH.edge_style==="arc"?0.06:0.045)*base;const cx=mx-dy/h*k,cy=my+dx/h*k;d=`M${a.x},${a.y} Q${cx},${cy} ${b.x},${b.y}`;}
    const p=el("path",{d,stroke:TH.node_edge,"stroke-width":"1","stroke-opacity":"0.18",fill:"none","stroke-linecap":"round"});p.dataset.s=e.source;p.dataset.t=e.target;eg.appendChild(p);edgeEls.push(p);});
  NODES.forEach(n=>{const pt=pos[n.id];if(!pt)return;const isCore=FOUND.has(n.id),r=relevance(n);
    const g=el("g",{transform:`translate(${pt.x},${pt.y})`});g.style.cursor="pointer";g.dataset.id=n.id;g.tabIndex=0;g.setAttribute("role","button");g.setAttribute("aria-label",nm(n,lang));
    g.onclick=()=>select(n.id);g.onkeydown=(ev)=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();select(n.id);}};
    if(TH.node_shape==="rounded_rect"){
      const fp=isCore?base*0.022:base*0.017,label=nm(n,lang),w=Math.max(label.length*fp*0.62+24,base*0.1),h=fp*2.1;
      if(r>0.85&&TH.centrality_by!=="size")g.appendChild(el("circle",{r:w*0.6,fill:"url(#halo)"}));
      g.appendChild(el("rect",{x:-w/2,y:-h/2,width:w,height:h,rx:6,fill:TH.node_core,"fill-opacity":(0.14+r*0.34).toFixed(2),stroke:TH.accent,"stroke-opacity":(0.4+r*0.5).toFixed(2),"stroke-width":isCore?"1.4":"0.7"}));
      const t=el("text",{"text-anchor":"middle","dominant-baseline":"central","font-family":TH.font_display,fill:TH.text_on_bg,"fill-opacity":(0.72+r*0.28).toFixed(2),"font-size":fp.toFixed(1),"letter-spacing":TH.letterspacing});t.textContent=label;g.appendChild(t);
    } else {
      const R=periR+r*(coreR-periR);
      const ntype=n.type||"concept";
      /* flat warm circle */
      const c=el("circle",{r:R.toFixed(1),fill:TH.node_core,"fill-opacity":(0.50+r*0.40).toFixed(2),stroke:TH.ink,"stroke-opacity":(0.06+r*0.10).toFixed(2),"stroke-width":"0.8"});
      g.appendChild(c);
      /* type icon — simple geometric symbol */
      const sc=R*0.36,sw=Math.max(0.6,R*0.068).toFixed(2);
      const ia={stroke:TH.ink,"stroke-width":sw,"stroke-linecap":"round","stroke-linejoin":"round",fill:"none","stroke-opacity":"0.24"};
      if(ntype==="theory"){
        /* open book: two pages meeting at spine */
        const bx=sc*0.72,by1=sc*0.50,by2=sc*0.68,bt=sc*0.70;
        g.appendChild(el("path",Object.assign({},ia,{d:`M0,${-bt.toFixed(1)} L${-bx.toFixed(1)},${-by1.toFixed(1)} L${-bx.toFixed(1)},${by2.toFixed(1)} L0,${by2.toFixed(1)} L${bx.toFixed(1)},${by2.toFixed(1)} L${bx.toFixed(1)},${-by1.toFixed(1)} Z`})));
        g.appendChild(el("line",Object.assign({},ia,{x1:"0",y1:(-bt).toFixed(1),x2:"0",y2:by2.toFixed(1)})));
        g.appendChild(el("line",Object.assign({},ia,{"stroke-opacity":"0.12",x1:(-sc*0.55).toFixed(1),y1:(-sc*0.08).toFixed(1),x2:(-sc*0.08).toFixed(1),y2:(-sc*0.08).toFixed(1)})));
      } else if(ntype==="method"){
        /* three horizontal lines, middle widest */
        [[0.58,-0.38],[0.68,0],[0.46,0.38]].forEach(([hw,fy])=>{
          g.appendChild(el("line",Object.assign({},ia,{x1:(-sc*hw).toFixed(1),y1:(sc*fy).toFixed(1),x2:(sc*hw).toFixed(1),y2:(sc*fy).toFixed(1)})));
        });
      } else if(ntype==="tool"){
        /* diamond */
        g.appendChild(el("path",Object.assign({},ia,{d:`M0,${(-sc*0.72).toFixed(1)} L${(sc*0.62).toFixed(1)},0 L0,${(sc*0.72).toFixed(1)} L${(-sc*0.62).toFixed(1)},0 Z`})));
      } else {
        /* concept: outer ring + inner dot */
        g.appendChild(el("circle",Object.assign({},ia,{r:(sc*0.65).toFixed(1)})));
        g.appendChild(el("circle",{r:(sc*0.20).toFixed(1),fill:TH.ink,"fill-opacity":"0.18",stroke:"none"}));
      }
      /* label below the circle */
      const fp=Math.min(base*0.016,R*0.52);
      const label=nm(n,lang);
      const t=el("text",{"text-anchor":"middle","font-family":TH.font_display,"fill":TH.ink,"fill-opacity":"0.80","font-size":fp.toFixed(1)});
      t.setAttribute("y",(R+fp*1.35).toFixed(1));t.textContent=label;g.appendChild(t);
    }
    ng.appendChild(g);nodeEls[n.id]=g;});
  if(cur)paint(cur);
}

const defs=document.getElementById("defs");
(function(){const c=el("radialGradient",{id:"core",cx:"50%",cy:"50%",r:"50%"});
  c.appendChild(el("stop",{offset:"0%","stop-color":"#ffffff","stop-opacity":"0.95"}));c.appendChild(el("stop",{offset:"55%","stop-color":TH.node_core}));c.appendChild(el("stop",{offset:"100%","stop-color":TH.ink,"stop-opacity":"0.6"}));defs.appendChild(c);
  const h=el("radialGradient",{id:"halo",cx:"50%",cy:"50%",r:"50%"});h.appendChild(el("stop",{offset:"0%","stop-color":TH.accent,"stop-opacity":"0.45"}));h.appendChild(el("stop",{offset:"100%","stop-color":TH.accent,"stop-opacity":"0"}));defs.appendChild(h);
  const f=el("filter",{id:"tshadow",x:"-40%",y:"-40%",width:"180%",height:"180%"});f.appendChild(el("feDropShadow",{dx:"0",dy:"0",stdDeviation:"3","flood-color":"#000000","flood-opacity":"0.92"}));defs.appendChild(f);})();

function showEdgeLabels(id){
  const elg=document.getElementById("elabels");elg.innerHTML="";
  if(!id)return;
  const base=Math.min(W,H),fp=base*0.0145;
  EDGES.forEach(e=>{
    if(e.source!==id&&e.target!==id)return;
    const a=pos[e.source],b=pos[e.target];if(!a||!b)return;
    const label=rel(e,lang);if(!label)return;
    /* midpoint of the bezier curve (t=0.5 approximation: just lerp endpoints) */
    const mx=(a.x+b.x)/2,my=(a.y+b.y)/2;
    /* direction arrow: → if source==id, ← if target==id */
    const arrow=e.source===id?" →":" ←";
    const txt=label+arrow;
    const tw=txt.length*fp*0.60+14;
    const bg=el("rect",{x:(mx-tw/2).toFixed(1),y:(my-fp*0.92).toFixed(1),
      width:tw.toFixed(1),height:(fp*1.7).toFixed(1),rx:"4",
      fill:TH.bg_css,"fill-opacity":"0.92",
      stroke:TH.accent,"stroke-opacity":"0.4","stroke-width":"0.5"});
    const t=el("text",{"text-anchor":"middle","x":mx.toFixed(1),"y":(my+fp*0.52).toFixed(1),
      "font-family":TH.font_body,"font-size":fp.toFixed(1),
      fill:TH.ink,"fill-opacity":"0.80","letter-spacing":"0.025em"});
    t.textContent=txt;
    elg.appendChild(bg);elg.appendChild(t);
  });
}

function paint(id){
  /* build connected set for dimming unrelated nodes */
  const conn=new Set([id]);
  EDGES.forEach(e=>{if(e.source===id)conn.add(e.target);if(e.target===id)conn.add(e.source);});
  Object.values(nodeEls).forEach(g=>{
    const nid=g.dataset.id,nn=byId[nid],rr=relevance(nn);
    const s=g.querySelector("circle:last-of-type, rect"),t=g.querySelector("text");if(!s)return;
    if(nid===id){
      s.setAttribute("stroke",TH.ink);s.setAttribute("stroke-opacity","0.90");s.setAttribute("stroke-width","2.4");
      g.style.opacity="1";
    } else if(conn.has(nid)){
      s.setAttribute("stroke",TH.accent);s.setAttribute("stroke-opacity",(0.5+rr*0.4).toFixed(2));s.setAttribute("stroke-width","1.2");
      g.style.opacity="1";
    } else {
      s.setAttribute("stroke",TH.accent);s.setAttribute("stroke-opacity",(0.1+rr*0.15).toFixed(2));s.setAttribute("stroke-width","0.6");
      g.style.opacity="0.22";
    }
  });
  edgeEls.forEach(p=>{const on=p.dataset.s===id||p.dataset.t===id;p.setAttribute("stroke-opacity",on?"0.75":"0.06");p.setAttribute("stroke-width",on?"2.0":"0.8");});
  showEdgeLabels(id);
}

const STR={en:{tour:"start tour",next:"next ›",hint:"Tap any concept to read its full archive — what it is, why it matters, where it sits, and a key line. Or take the guided tour. ← → to step, F to present.",leg:"● solid = core   ○ faint = peripheral",search:"Search…",present:"⤢ present",what:"What it is",why:"Why it matters",position:"Its place in the system",rels:"Connections",src:"sources"},
            zh:{tour:"开始引导",next:"下一 ›",hint:"点按任一概念，读它的完整档案——是什么、为何重要、处于何位、关键一句。或循引导徐行。← → 翻页，F 演示。",leg:"● 实者为本   ○ 淡者为末",search:"搜索…",present:"⤢ 演示",what:"是什么",why:"为何重要",position:"在体系中的位置",rels:"关联",src:"出处"}};

function render(id){
  const n=byId[id],s=STR[lang];paint(id);
  const what=pf(n,"what",lang)||sm(n,lang), why=pf(n,"why",lang), position=pf(n,"position",lang), quote=pf(n,"quote",lang), qsrc=(n.profile||{}).quote_source||"";
  const conns=EDGES.filter(e=>e.source===id||e.target===id).map(e=>{const o=e.source===id?e.target:e.source,d=e.source===id?"→":"←";return `<span class="rel" data-go="${o}">${rel(e,lang)} ${d} ${nm(byId[o],lang)}</span>`;}).join("");
  const altName = lang==="en" ? ((n.name||{}).zh||"") : ((n.name||{}).en||"");
  const typeLabel={theory:lang==="zh"?"根本理念":"major work",method:lang==="zh"?"方法":"method",tool:lang==="zh"?"工具":"tool",concept:lang==="zh"?"概念":"concept"}[n.type||"concept"];
  const diff=n.difficulty||"intermediate";
  const CHAP_EN={foundational:"Chapter I · Foundations",intermediate:"Chapter II · Core Ideas",advanced:"Chapter III · Deep Cuts"};
  const CHAP_ZH={foundational:"第一章 · 基础",intermediate:"第二章 · 核心",advanced:"第三章 · 深入"};
  const chapLabel=(lang==="zh"?CHAP_ZH:CHAP_EN)[diff]||"";
  const tourPos=(META.tour||[]).indexOf(id);
  const posLabel=tourPos>=0?`${tourPos+1} / ${(META.tour||[]).length}`:"";
  const kicker=`${chapLabel}${posLabel?" — #"+posLabel:""} · ${typeLabel}`;
  let html = `<div class="kicker">${kicker}</div><div class="nm">${nm(n,lang)}</div><div class="alt">${altName}</div><div class="archive">`;
  if(what){ html+=`<div class="seg-label">${s.what}</div><div class="seg-body">${what}</div>`; }
  if(why){ html+=`<div class="seg-label">${s.why}</div><div class="seg-body">${why}</div>`; }
  if(quote){ html+=`<div class="quote" style="border-color:${TH.accent}66"><div class="q">${quote}</div>${qsrc?`<div class="qs">— ${qsrc}</div>`:""}</div>`; }
  if(position){ html+=`<div class="seg-label">${s.position}</div><div class="seg-body">${position}</div>`; }
  html+=`<div class="seg-label">${s.rels}</div><div class="rels">${conns}</div>`;
  const src=(n.sources||[]).filter(Boolean);
  if(src.length){ const lbl = (G.source_mode==="corpus") ? (lang==="zh"?"出自你的文档":"from your documents") : s.src; html+=`<div class="qs" style="margin-top:14px">${lbl}: ${src.join(" · ")}</div>`; }
  html+=`</div>`;
  const insp=document.getElementById("inspector"); insp.innerHTML=html;
  insp.querySelectorAll(".rel").forEach(r=>r.onclick=()=>select(r.dataset.go));
  insp.scrollTop=0;
}

function buildControls(){
  const c=document.getElementById("controls");c.innerHTML="";
  const seg=document.createElement("div");seg.className="seg";seg.style.borderColor=TH.accent+"66";
  const en=document.createElement("button"),zh=document.createElement("button");en.textContent="EN";zh.textContent="中";en.id="b-en";zh.id="b-zh";en.onclick=()=>setLang("en");zh.onclick=()=>setLang("zh");
  seg.appendChild(en);seg.appendChild(zh);c.appendChild(seg);
  const tour=document.createElement("button");tour.className="pill";tour.id="b-tour";tour.style.borderColor=TH.accent+"66";tour.style.color=TH.text_on_bg;tour.onclick=()=>doTour(1);c.appendChild(tour);
  const prev=document.createElement("button");prev.className="pill";prev.textContent="‹";prev.style.borderColor=TH.accent+"66";prev.style.color=TH.text_on_bg;prev.onclick=()=>doTour(-1);c.appendChild(prev);
  const search=document.createElement("input");search.type="text";search.id="search";search.style.borderColor=TH.accent+"66";search.style.color=TH.text_on_bg;search.oninput=(e)=>doSearch(e.target.value);c.appendChild(search);
  const pos=document.createElement("span");pos.className="pos";pos.id="pos";c.appendChild(pos);
}
function setLang(l){
  lang=l;const en=document.getElementById("b-en"),zh=document.getElementById("b-zh");
  en.style.background=l==="en"?TH.accent:"transparent";en.style.color=l==="en"?TH.ink:TH.text_on_bg;
  zh.style.background=l==="zh"?TH.accent:"transparent";zh.style.color=l==="zh"?TH.ink:TH.text_on_bg;
  document.getElementById("b-tour").textContent=tourIdx<0?STR[l].tour:STR[l].next;
  document.getElementById("search").placeholder=STR[l].search;document.getElementById("legend").textContent=STR[l].leg;document.getElementById("presentBtn").textContent=STR[l].present;
  Object.entries(nodeEls).forEach(([id,g])=>{const t=g.querySelector("text");if(t)t.textContent=nm(byId[id],lang);});
  document.getElementById("h-expert").textContent=(G.expert||{})[lang]||(G.expert||{}).en||"";
  document.getElementById("h-domain").textContent=(G.domain||{})[lang]||(G.domain||{}).en||"";
  if(cur)render(cur);else document.getElementById("inspector").innerHTML=`<div class="hint">${STR[l].hint}</div>`;
}
function select(id){cur=id;tourIdx=-1;document.getElementById("pos").textContent="";document.getElementById("b-tour").textContent=STR[lang].tour;render(id);}
function doTour(dir){const tour=META.tour||[];if(!tour.length)return;if(dir>0&&tourIdx<0)tourIdx=0;else tourIdx=Math.max(0,Math.min(tour.length-1,tourIdx+dir));cur=tour[tourIdx];document.getElementById("pos").textContent=`${tourIdx+1} / ${tour.length}`;document.getElementById("b-tour").textContent=STR[lang].next;render(cur);}
function doSearch(q){q=(q||"").trim().toLowerCase();Object.entries(nodeEls).forEach(([id,g])=>{const n=byId[id];const hay=((n.name||{}).en||"")+" "+((n.name||{}).zh||"")+" "+sm(n,lang)+" "+pf(n,"what",lang);g.style.opacity=(!q||hay.toLowerCase().includes(q))?"1":"0.18";});}

const pb=document.getElementById("presentBtn");pb.style.borderColor=TH.accent+"66";pb.style.color=TH.text_on_bg;pb.onclick=togglePresent;
function togglePresent(){if(!document.fullscreenElement){document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen();document.body.classList.add("present");}else{document.exitFullscreen&&document.exitFullscreen();document.body.classList.remove("present");}setTimeout(computeLayout,120);}
document.addEventListener("fullscreenchange",()=>{if(!document.fullscreenElement)document.body.classList.remove("present");setTimeout(computeLayout,120);});
document.addEventListener("keydown",(e)=>{if(e.target.tagName==="INPUT")return;if(e.key==="ArrowRight")doTour(1);else if(e.key==="ArrowLeft")doTour(-1);else if(e.key==="f"||e.key==="F")togglePresent();else if(e.key==="Escape"&&document.body.classList.contains("present"))document.body.classList.remove("present");});
let rT;window.addEventListener("resize",()=>{clearTimeout(rT);rT=setTimeout(computeLayout,150);});

document.getElementById("svg-desc").textContent="Concept graph of "+((G.expert||{}).en||"");
const rat=(lang==="zh"?TH.rationale_zh:TH.rationale_en)||TH.rationale_en||"";
document.getElementById("rationale").textContent=rat?("Theme · "+TH.name+" — "+rat):("Theme · "+TH.name);

buildControls();computeLayout();setLang(lang);
</script>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    graph = json.load(open(sys.argv[1], encoding="utf-8"))
    theme = None
    out = "knowledge_map.html"
    if len(sys.argv) >= 3 and sys.argv[2].endswith(".json"):
        theme = json.load(open(sys.argv[2], encoding="utf-8"))
        out = sys.argv[3] if len(sys.argv) >= 4 else out
    elif len(sys.argv) >= 3:
        out = sys.argv[2]
    title = (graph.get("expert") or {}).get("en") or "Knowledge Map"
    Path(out).write_text(build_html(graph, theme, title=title), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
