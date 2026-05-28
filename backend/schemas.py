"""
schemas.py — Pydantic models for structured extraction (v3).

Adopts the cookbook's structured-output pattern: instead of hand-parsing JSON
with regex + retries, we define the output SHAPE as a Pydantic model and let
`client.messages.parse(..., output_format=Model)` guarantee a validated object.

All human-readable fields stay bilingual ({en, zh}) per the Wittgenstein
principle — each language is its own world, extracted independently (see
pipeline.extract_bilingual).
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


Lang = Literal["en", "zh"]
NodeType = Literal["concept", "method", "theory", "tool"]
Relation = Literal["depends_on", "part_of", "contrasts_with", "leads_to",
                   "applies", "subtype_of"]


class Concept(BaseModel):
    name: str
    type: NodeType = "concept"
    # one-line description, used as disambiguation context during resolution
    # (the cookbook's key trick: "Armstrong the astronaut" vs "the trumpeter")
    description: str = ""
    relevance: float = Field(0.5, ge=0.0, le=1.0)


class Link(BaseModel):
    source: str
    target: str
    relation: Relation = "depends_on"
    in_system: bool = True
    relevance: float = Field(0.5, ge=0.0, le=1.0)
    evidence: str = ""


class ExtractedGraph(BaseModel):
    """One language's view of the graph, extracted in a single pass."""
    concepts: list[Concept]
    links: list[Link]


class NodeProfile(BaseModel):
    """The four-part ARCHIVE that gives a node real depth (vs a one-line card).
    This is the core of closing the gap with Understand-Anything's node inspector.
    Each field is bilingual-ready: the pipeline runs this per-language."""
    what: str = ""        # what the concept IS (a real explanation, 2-3 sentences)
    why: str = ""         # why it MATTERS within this body of knowledge
    position: str = ""    # its PLACE in the system: what it grounds / depends on
    quote: str = ""       # a key QUOTATION or canonical example, with source
    quote_source: str = ""


class ProfiledConcept(BaseModel):
    name: str
    profile: NodeProfile


class SourcedConcept(BaseModel):
    """A concept extracted FROM a document — carries which chunk it came from
    so the graph can point back to the exact passage (provenance)."""
    name: str
    type: NodeType = "concept"
    description: str = ""
    relevance: float = Field(0.5, ge=0.0, le=1.0)
    chunk_ids: list[str] = []   # which source chunks mention it


class SourcedLink(BaseModel):
    source: str
    target: str
    relation: Relation = "depends_on"
    evidence: str = ""
    chunk_id: str = ""          # the chunk supporting this link


class DocExtraction(BaseModel):
    """Entities + relations extracted from ONE document chunk."""
    concepts: list[SourcedConcept]
    links: list[SourcedLink]


class Cluster(BaseModel):
    canonical: str
    aliases: list[str]


class ResolvedClusters(BaseModel):
    clusters: list[Cluster]


class HubProfile(BaseModel):
    """Rich profile for a high-degree hub node (cookbook's summarization step)."""
    summary: str
    key_facts: list[str]


class ScopePlan(BaseModel):
    scope: Literal["bounded", "moderate", "sprawling"]
    max_depth: int = Field(2, ge=2, le=4)
    max_nodes: int = Field(50, ge=25, le=120)
    rationale_en: str = ""
    rationale_zh: str = ""


class TourPlan(BaseModel):
    difficulty: dict[str, Literal["foundational", "intermediate", "advanced"]]
    tour: list[str]
