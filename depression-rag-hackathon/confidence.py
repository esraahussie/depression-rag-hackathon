"""
Objective confidence scoring for MindCare RAG responses.

The score is computed from retrieval/rerank signals and citation grounding —
never from an LLM self-assessment.
"""

import math
import re

from settings import RERANK_RELEVANCE_THRESHOLD, FUSED_RELEVANCE_THRESHOLD, USE_RERANKING
from relevance import get_relevance_score


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def normalize_score(score: float | None) -> float:
    """
    Map a raw rerank or fused score to [0, 1].
    Centered at the configured relevance threshold (≈0.5 at cutoff).
    """
    if score is None:
        return 0.0
    center = RERANK_RELEVANCE_THRESHOLD if USE_RERANKING else FUSED_RELEVANCE_THRESHOLD
    scale = 2.0 if USE_RERANKING else 80.0
    return _sigmoid((score - center) / scale)


def _citation_grounding_ratio(answer: str, valid_ids: set[int]) -> float:
    """Fraction of substantive sentences that carry at least one valid citation."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    if not sentences:
        return 0.0
    cited = 0
    for sentence in sentences:
        ids = {int(m) for m in re.findall(r"\[(\d+)\]", sentence)}
        if ids & valid_ids:
            cited += 1
    return cited / len(sentences)


def _chunk_agreement(results: list[dict], threshold: float) -> float:
    """Share of top retrieved chunks whose score meets the relevance threshold."""
    if not results:
        return 0.0
    top = results[: min(3, len(results))]
    above = sum(1 for r in top if (get_relevance_score(r) or float("-inf")) >= threshold)
    return above / len(top)


def compute_confidence(
    *,
    status: str,
    relevant_results: list[dict],
    cited_results: list[dict],
    answer: str,
    valid_citation_ids: set[int],
) -> float:
    """
    Weighted combination of:
      - top retrieval/rerank score        (35%)
      - mean score of cited chunks        (25%)
      - agreement among top chunks        (15%)
      - citation grounding in the answer  (15%)
      - cited-chunk coverage              (10%)

    Out-of-scope → 0.0. Insufficient evidence is capped below 0.45.
    """
    if status == "out_of_scope":
        return 0.0

    if not relevant_results:
        return 0.05 if status == "insufficient" else 0.0

    threshold = RERANK_RELEVANCE_THRESHOLD if USE_RERANKING else FUSED_RELEVANCE_THRESHOLD
    top_score = max(get_relevance_score(r) or 0.0 for r in relevant_results)
    top_norm = normalize_score(top_score)

    if cited_results:
        cited_avg = sum(normalize_score(get_relevance_score(r)) for r in cited_results) / len(cited_results)
    else:
        cited_avg = top_norm * 0.5

    agreement = _chunk_agreement(relevant_results, threshold)
    grounding = _citation_grounding_ratio(answer, valid_citation_ids) if valid_citation_ids else 0.0
    coverage = min(len(cited_results) / max(len(relevant_results), 1), 1.0)

    raw = (
        0.35 * top_norm
        + 0.25 * cited_avg
        + 0.15 * agreement
        + 0.15 * grounding
        + 0.10 * coverage
    )

    confidence = round(max(0.0, min(1.0, raw)), 2)

    if status == "insufficient":
        confidence = min(confidence, 0.45)

    return confidence
