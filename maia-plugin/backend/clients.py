"""
clients.py — LLM + web search wrappers (v3, two-model + structured outputs).

Cookbook lessons applied:
  * TWO models. Haiku does high-volume, schema-constrained extraction where
    speed/cost dominate. Sonnet does resolution + summarization where the model
    must weigh conflicting evidence. (We no longer use Opus for everything.)
  * STRUCTURED OUTPUTS. parse_model() returns a validated Pydantic object — no
    regex, no JSON decode errors, no defensive isinstance checks.

llm_json() is kept ONLY for tool-using calls (web search), where the parse()
helper can't be used; everything else should go through parse_model().
"""
from __future__ import annotations
import asyncio
import json
import re

import anthropic

# Cookbook split: cheap+fast for extraction, stronger for judgement.
EXTRACTION_MODEL = "claude-haiku-4-5"
SYNTHESIS_MODEL = "claude-sonnet-4-6"

_client = anthropic.AsyncAnthropic()


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


# --- structured output (preferred path) ----------------------------------
async def parse_model(prompt: str, output_format, *,
                      model: str = EXTRACTION_MODEL, max_tokens: int = 2048,
                      system: str | None = None, retries: int = 2):
    """Return a validated Pydantic object, or None on repeated failure."""
    for attempt in range(retries + 1):
        try:
            kwargs = dict(model=model, max_tokens=max_tokens,
                          messages=[{"role": "user", "content": prompt}],
                          output_format=output_format)
            if system:
                kwargs["system"] = system
            resp = await _client.messages.parse(**kwargs)
            return resp.parsed_output
        except Exception as e:
            if attempt == retries:
                print(f"  [parse_model] gave up: {e}")
                return None
            await asyncio.sleep(1.2 * (attempt + 1))
    return None


# --- json fallback (only for tool-using calls) ----------------------------
async def llm_json(prompt: str, *, model: str = SYNTHESIS_MODEL,
                   max_tokens: int = 2048, tools=None, retries: int = 2):
    system = ("Output ONLY valid JSON. No prose, no markdown fences.")
    for attempt in range(retries + 1):
        try:
            kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                          messages=[{"role": "user", "content": prompt}])
            if tools:
                kwargs["tools"] = tools
            resp = await _client.messages.create(**kwargs)
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            return json.loads(_strip_fences(text))
        except Exception as e:
            if attempt == retries:
                print(f"  [llm_json] gave up: {e}")
                return None
            await asyncio.sleep(1.2 * (attempt + 1))
    return None


# --- web search -----------------------------------------------------------
async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Return [{title, url, snippet}]. Swap body for your search provider."""
    try:
        resp = await _client.messages.create(
            model=SYNTHESIS_MODEL, max_tokens=2048,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content":
                       f"Search the web for: {query}. Return authoritative sources."}],
        )
        results = []
        for block in resp.content:
            if getattr(block, "type", "") == "web_search_tool_result":
                for item in getattr(block, "content", []) or []:
                    results.append({"title": getattr(item, "title", ""),
                                    "url": getattr(item, "url", ""),
                                    "snippet": getattr(item, "encrypted_content", "")[:500]})
        if not results:
            text = "".join(b.text for b in resp.content if b.type == "text")
            results = [{"title": "", "url": "", "snippet": text[:2000]}]
        return results[:max_results]
    except Exception as e:
        print(f"  [web_search] error: {e}")
        return []


class Semaphored:
    def __init__(self, limit: int = 5):
        self.sem = asyncio.Semaphore(limit)

    async def run(self, coro):
        async with self.sem:
            return await coro


# --- subagent exploration (isolated context for low-relevance concepts) ----
async def subagent_explore(expert: str, domain: str, concept_name: str,
                           lang: str = "en") -> dict | None:
    """Isolated-context exploration of a peripheral concept. The subagent does
    its own (possibly wandering) searching and returns only a compact verdict,
    so noise never enters the main context. Skeptical by design."""
    system = ("You are an isolated research subagent. Explore one peripheral "
              "concept via web search and return ONLY a compact JSON verdict. "
              "Be skeptical: if it does not genuinely belong, say keep=false.")
    prompt = f"""Target: {expert} — {domain}. Peripheral concept: "{concept_name}".
Search and decide. Output JSON ONLY:
{{"keep": true_or_false,
  "summary": {{"en":"...","zh":"..."}},
  "sources": ["url"],
  "neighbors": [{{"name":{{"en":"...","zh":"..."}},
    "relation":"depends_on|part_of|contrasts_with|leads_to|applies",
    "in_system": true_or_false, "relevance": 0.0_to_1.0, "evidence":"phrase"}}]}}
keep=false (empty neighbors) if it does not belong to {expert}'s {domain}."""
    try:
        resp = await _client.messages.create(
            model=EXTRACTION_MODEL, max_tokens=2048, system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        data = json.loads(_strip_fences(text))
        if not data.get("keep", True):
            data["neighbors"] = []
        return data
    except Exception as e:
        print(f"  [subagent] {concept_name}: {e}")
        return None
