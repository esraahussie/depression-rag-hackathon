"""
STEP 10a: GENERATION — Groq LLM when available, otherwise extractive fallback.

Both paths receive pre-assigned citation IDs and must produce [n] markers
that map to the numbered sources.
"""

import re

from settings import GENERATION_MODEL, GENERATION_SYSTEM_PROMPT
from citations import build_context_with_citations, build_source_legend
from config import client
from retrieval import simple_tokenize


def _token_overlap_score(query_tokens: set[str], text: str) -> float:
    text_tokens = set(simple_tokenize(text))
    if not query_tokens or not text_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / len(query_tokens)


def _best_sentences(query: str, result: dict, max_sentences: int = 2) -> list[str]:
    """Pick the most query-relevant sentences from one chunk (extractive fallback)."""
    query_tokens = set(simple_tokenize(query))
    text = result.get("text", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 6]
    if not sentences:
        return [text[:400].strip()] if text.strip() else []

    ranked = sorted(sentences, key=lambda s: _token_overlap_score(query_tokens, s), reverse=True)
    return ranked[:max_sentences]


def generate_extractive_answer(query: str, cited_results: list[dict]) -> str:
    """
    Build a grounded answer from retrieved chunks without an LLM.
    Each sentence is tagged with the citation_id of its source chunk.
    """
    if not cited_results:
        return ""

    parts: list[str] = []
    for result in cited_results[:3]:
        cid = result["citation_id"]
        for sentence in _best_sentences(query, result):
            if not sentence.endswith((".", "!", "?")):
                sentence += "."
            parts.append(f"{sentence} [{cid}]")

    if not parts:
        top = cited_results[0]
        cid = top["citation_id"]
        snippet = top.get("text", "")[:400].strip()
        if snippet and not snippet.endswith((".", "!", "?")):
            snippet += "."
        return f"{snippet} [{cid}]" if snippet else ""

    return " ".join(parts)


def generate_groq_answer(query: str, cited_results: list[dict], model: str = GENERATION_MODEL) -> str:
    context_block = build_context_with_citations(cited_results)
    source_legend = build_source_legend(cited_results)
    valid_ids = ", ".join(str(r["citation_id"]) for r in cited_results)

    user_prompt = (
        f"Source Index (ONLY these citation IDs exist: {valid_ids}):\n"
        f"{source_legend}\n\n"
        f"Context passages:\n\n{context_block}\n\n"
        f"Question: {query}\n\n"
        f"Answer using ONLY the passages above. Cite every claim with [n] where n is "
        f"one of: {valid_ids}. Do NOT use any other citation number."
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_answer(query: str, cited_results: list[dict], model: str = GENERATION_MODEL) -> str:
    """
    Generate an answer from pre-numbered retrieval results.
    Uses Groq when configured; falls back to extractive sentence selection.
    """
    if not cited_results:
        return ""

    if client is not None:
        try:
            return generate_groq_answer(query, cited_results, model=model)
        except Exception:
            pass

    return generate_extractive_answer(query, cited_results)
