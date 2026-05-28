"""
planner.py — depth auto-assessment + probabilistic subagent scheduler (v3).
assess_scope now uses structured output (ScopePlan).
"""
from __future__ import annotations
import random

from clients import parse_model, SYNTHESIS_MODEL
from schemas import ScopePlan


# ---------------------------------------------------------------------------
# Depth auto-assessment
# ---------------------------------------------------------------------------
async def assess_scope(expert: str, domain: str) -> dict:
    """Decide max_depth / max_nodes from the nature of the subject.

    Bounded+convergent (one classic text) -> shallow but complete.
    Sprawling+fuzzy (a whole discipline)  -> deeper + wider, stricter filtering.
    """
    plan = await parse_model(
        f"""Assess the body of knowledge: {expert} — {domain}.
Is the corpus BOUNDED (one classic text, a tight theory) or SPRAWLING
(an entire discipline, fuzzy borders)? Bounded+convergent -> shallow but
complete. Sprawling+fuzzy -> deeper and wider with stricter relevance filtering.
Choose scope, max_depth (2-4), max_nodes (25-120), and a one-line rationale in
both English and Chinese.""",
        ScopePlan, model=SYNTHESIS_MODEL)
    if not plan:
        return {"scope": "moderate", "max_depth": 2, "max_nodes": 50,
                "rationale_en": "Defaulted to moderate scope.",
                "rationale_zh": "采用默认的中等范围。"}
    return {"scope": plan.scope, "max_depth": plan.max_depth,
            "max_nodes": plan.max_nodes, "rationale_en": plan.rationale_en,
            "rationale_zh": plan.rationale_zh}


# ---------------------------------------------------------------------------
# Probabilistic subagent scheduler
# ---------------------------------------------------------------------------
class RelevanceScheduler:
    """Maps relevance (0-1) to P(subagent). Lower relevance -> higher P."""

    def __init__(self, floor: float = 0.05, ceiling: float = 0.9, seed=None):
        self.floor = floor
        self.ceiling = ceiling
        self.rng = random.Random(seed)

    @staticmethod
    def combine(llm_score: float, depth: int, parent_count: int,
                max_depth: int) -> float:
        """Fuse LLM judgement (0.6) + shallowness (0.25) + parent support (0.15)."""
        depth_term = 1.0 - (depth / max(1, max_depth + 1))
        parent_term = min(1.0, parent_count / 3.0)
        score = 0.6 * llm_score + 0.25 * depth_term + 0.15 * parent_term
        return max(0.0, min(1.0, score))

    def p_subagent(self, relevance: float) -> float:
        p = self.ceiling - (self.ceiling - self.floor) * relevance
        return max(self.floor, min(self.ceiling, p))

    def decide(self, relevance: float) -> bool:
        return self.rng.random() < self.p_subagent(relevance)
