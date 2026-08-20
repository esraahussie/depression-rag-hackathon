"""
STEP 10a: GENERATION — Groq LLM when available, otherwise extractive fallback.

Both paths receive pre-assigned citation IDs and must produce [n] markers
that map to the numbered sources.
"""

import re

from settings import GENERATION_MODEL, GENERATION_SYSTEM_PROMPT
from citations import build_context_with_citations, build_source_legend
from config import client
from language import GENERATION_SYSTEM_PROMPT_ARZ, localize_extractive_answer
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


def generate_groq_answer(
    query: str,
    cited_results: list[dict],
    model: str = GENERATION_MODEL,
    response_language: str = "en",
    display_query: str | None = None,
) -> str:
    context_block = build_context_with_citations(cited_results)
    source_legend = build_source_legend(cited_results)
    valid_ids = ", ".join(str(r["citation_id"]) for r in cited_results)
    arabic = response_language == "arz"
    system_prompt = GENERATION_SYSTEM_PROMPT_ARZ if arabic else GENERATION_SYSTEM_PROMPT
    question_text = display_query or query
    answer_instruction = (
        f"جاوب بالمصري العامي القاهري باستخدام الفقرات فوق بس — مش فصحى. "
        f"حط [n] بعد كل معلومة، و n لازم تكون واحدة من: {valid_ids}. متستخدمش رقم تاني. "
        f"متترجمش الفقرات حرفي؛ لخّص المعنى الطبي بالمصري. "
        f"متستخدمش ** ولا * ولا أي ماركداون."
        if arabic
        else (
            f"Answer using ONLY the passages above. Cite every claim with [n] where n is "
            f"one of: {valid_ids}. Do NOT use any other citation number. "
            f"Do not use markdown (no **bold**, no *asterisks*, no headings)."
        )
    )

    user_prompt = (
        f"Source Index (ONLY these citation IDs exist: {valid_ids}):\n"
        f"{source_legend}\n\n"
        f"Context passages:\n\n{context_block}\n\n"
        f"Question: {question_text}\n\n"
        f"{answer_instruction}"
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_answer(
    query: str,
    cited_results: list[dict],
    model: str = GENERATION_MODEL,
    response_language: str = "en",
    display_query: str | None = None,
) -> str:
    """
    Generate an answer from pre-numbered retrieval results.
    Uses Groq when configured; falls back to extractive sentence selection.

    `query` is the English retrieval query (needed for extractive overlap).
    `display_query` is the original user question, used in the LLM prompt.
    """
    if not cited_results:
        return ""

    if client is not None:
        try:
            return generate_groq_answer(
                query,
                cited_results,
                model=model,
                response_language=response_language,
                display_query=display_query,
            )
        except Exception:
            pass

    extractive = generate_extractive_answer(query, cited_results)
    if response_language == "arz":
        return localize_extractive_answer(extractive)
    return extractive
