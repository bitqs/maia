"""
theme.py — the design-taste engine.

Jobs: "ultimately it comes down to taste." But taste isn't one style — it's the
judgement to pick the RIGHT style for each subject. A graph about Daoism and a
graph about quantum mechanics should not look the same.

This module asks Claude to read the subject's CHARACTER along a few axes, then
maps those axes to a concrete design system (palette, type, layout, motion).
UX legibility is a HARD FLOOR enforced regardless of theme: contrast, no text
crossed by edges, clear visual hierarchy. Aesthetics operate inside that floor.

Output is a ThemeSpec the dashboard consumes — the same graph.json can render
under whatever theme the subject calls for.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

from clients import parse_model, SYNTHESIS_MODEL


# --- the character axes the subject is read along -------------------------
class CharacterAxes(BaseModel):
    # each -1.0 .. 1.0
    classical_modern: float = Field(0.0, ge=-1, le=1)   # -1 classical, +1 modern
    eastern_western: float = Field(0.0, ge=-1, le=1)    # -1 eastern, +1 western
    humanistic_technical: float = Field(0.0, ge=-1, le=1)  # -1 human, +1 technical
    intuitive_rational: float = Field(0.0, ge=-1, le=1)  # -1 intuitive, +1 rational
    organic_geometric: float = Field(0.0, ge=-1, le=1)  # -1 organic, +1 geometric


# --- the concrete design system the dashboard renders ---------------------
class ThemeSpec(BaseModel):
    name: str                          # short label, e.g. "ink-wash", "blueprint"
    rationale_en: str = ""
    rationale_zh: str = ""

    # surface
    bg_style: Literal["ink", "deep_space", "gallery_white", "warm_paper",
                      "blueprint", "slate"] = "warm_paper"
    bg_css: str = ""                   # actual CSS background value

    # palette (hex)
    ink: str = "#1a1813"               # primary text / strongest nodes
    accent: str = "#c9bfa6"            # accent / highlight
    node_core: str = "#d8c89a"         # core node fill
    node_edge: str = "#c9bfa6"         # edge / connector
    text_on_bg: str = "#f3e9cf"        # body text over the bg

    # typography
    font_display: str = "var(--font-serif)"  # node glyphs / titles
    font_body: str = "var(--font-serif)"     # detail prose
    letterspacing: str = "0"

    # geometry
    layout: Literal["radial", "grid", "free", "layered", "orbital"] = "radial"
    edge_style: Literal["curved", "straight", "elbow", "arc"] = "curved"
    node_shape: Literal["circle", "rounded_rect", "diamond", "hexagon"] = "circle"

    # encoding of centrality
    centrality_by: Literal["solidity", "size", "glow", "elevation"] = "solidity"


CHARACTER_PROMPT = """Read the CHARACTER of this body of knowledge so we can
design a visual identity that fits it (not a generic graph).

Subject: {expert} — {domain}

Rate it on five axes, each from -1.0 to 1.0:
- classical_modern: ancient/timeless (-1) vs contemporary/cutting-edge (+1)
- eastern_western: East-Asian intellectual tradition (-1) vs Western (+1)
- humanistic_technical: humanities/arts/philosophy (-1) vs STEM/engineering (+1)
- intuitive_rational: poetic/experiential/holistic (-1) vs formal/analytic (+1)
- organic_geometric: flowing/natural (-1) vs structured/precise (+1)

Be decisive — push toward the extremes where the subject genuinely sits."""


THEME_PROMPT = """Given a subject's character axes, design a visual identity for
its knowledge graph. Honor these mappings as a starting point, then refine:

- classical+eastern+organic  -> ink-wash: warm dark paper bg, serif/brush type,
  radial layout, curved "water" connectors, centrality by solidity+glow.
- modern+technical+geometric -> blueprint: deep slate/navy bg, mono/sans type,
  grid or layered layout, straight/elbow connectors, centrality by size.
- humanistic+western+classical -> editorial: gallery off-white bg, elegant
  transitional serif, free/orbital layout, thin arc connectors, centrality by size.
- rational+technical          -> high-contrast cool palette; intuitive+organic
  -> warmer, softer palette with breathing room.

HARD UX FLOOR (never violate for aesthetics):
- text must have strong contrast against bg (WCAG AA)
- core/high-relevance nodes must read as the most prominent
- palette is cohesive: 1 dominant + 1 accent, not a rainbow

Subject: {expert} — {domain}
Axes: {axes}

Produce a complete ThemeSpec. bg_css must be a real CSS background value
(solid or gradient) consistent with bg_style. All colors hex. Give a one-line
rationale in English and Chinese for why this identity fits the subject."""


async def assess_character(expert: str, domain: str) -> CharacterAxes:
    axes = await parse_model(
        CHARACTER_PROMPT.format(expert=expert, domain=domain),
        CharacterAxes, model=SYNTHESIS_MODEL)
    return axes or CharacterAxes()


async def design_theme(expert: str, domain: str,
                       axes: CharacterAxes | None = None) -> ThemeSpec:
    if axes is None:
        axes = await assess_character(expert, domain)
    spec = await parse_model(
        THEME_PROMPT.format(expert=expert, domain=domain,
                            axes=axes.model_dump()),
        ThemeSpec, model=SYNTHESIS_MODEL, max_tokens=1500)
    return spec or ThemeSpec(name="warm-paper")
