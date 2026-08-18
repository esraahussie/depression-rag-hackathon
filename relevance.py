"""
Relevance / out-of-scope gating for MindCare RAG.

Uses retrieval scores (rerank + fused) — not LLM judgment — to decide whether
a query is supported, insufficiently evidenced, or outside scope.
"""

import re

from settings import (
    RERANK_RELEVANCE_THRESHOLD,
    INSUFFICIENT_EVIDENCE_THRESHOLD,
    FUSED_RELEVANCE_THRESHOLD,
    USE_RERANKING,
)

OUT_OF_SCOPE_MESSAGE = (
    "This question is outside the scope of MindCare. I can only answer questions "
    "related to the mental-health topics covered by the available clinical documents."
)

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "Your question appears related to mental health, but the available clinical "
    "documents do not contain enough information to answer it reliably. "
    "Please try rephrasing your question or consult a qualified healthcare professional."
)

# Obvious non-clinical intents — used as a secondary signal when retrieval is weak.
_OFF_TOPIC_PATTERNS = [
    re.compile(r"\bcapital of\b", re.I),
    re.compile(r"\bwrite (me )?(a )?(python|java|javascript|c\+\+|code|program)\b", re.I),
    re.compile(r"\bwho won\b.*\b(match|game|football|soccer|world cup)\b", re.I),
    re.compile(r"\btell me a joke\b", re.I),
    re.compile(r"\bhow (do|to) (i )?cook\b", re.I),
    re.compile(r"\brecipe for\b", re.I),
    re.compile(r"\bweather in\b", re.I),
]

_MENTAL_HEALTH_HINTS = re.compile(
    r"\b(depress|anxiety|mental|mood|suicid|phq|symptom|therapy|treatment|"
    r"medication|antidepress|screening|diagnos|psychiatric|psycholog|clinical|"
    r"disorder|sadness|hopeless|sleep|appetite|self.?harm|crisis|support|"
    r"guideline|who|nice|patient|caregiver|child|adolescent|adult|bipolar|"
    r"lithium|dosage|dose|prescri)\b",
    re.I,
)


def get_relevance_score(result: dict) -> float | None:
    """Best available relevance signal for one retrieved chunk."""
    rerank = result.get("rerank_score")
    if rerank is not None:
        return float(rerank)
    fused = result.get("fused_score")
    if fused is not None:
        return float(fused)
    return None


def is_obviously_off_topic(query: str) -> bool:
    return any(p.search(query) for p in _OFF_TOPIC_PATTERNS)


def query_has_mental_health_signal(query: str) -> bool:
    return bool(_MENTAL_HEALTH_HINTS.search(query))


def classify_retrieval(query: str, results: list[dict]) -> dict:
    """
    Classify retrieval outcome using objective scores.

    Returns:
        {
            "status": "supported" | "insufficient" | "out_of_scope",
            "relevant_results": [...],   # chunks that passed the relevance gate
            "top_score": float | None,
        }
    """
    if not results:
        return {"status": "out_of_scope", "relevant_results": [], "top_score": None}

    scored = [(r, get_relevance_score(r)) for r in results]
    scored_with_value = [(r, s) for r, s in scored if s is not None]
    top_score = max((s for _, s in scored_with_value), default=None)

    threshold = RERANK_RELEVANCE_THRESHOLD if USE_RERANKING else FUSED_RELEVANCE_THRESHOLD
    relevant = [r for r, s in scored_with_value if s >= threshold]

    obviously_off = is_obviously_off_topic(query)
    has_mh_signal = query_has_mental_health_signal(query)

    # No chunk clears the relevance bar.
    if not relevant:
        if has_mh_signal and not obviously_off:
            return {"status": "insufficient", "relevant_results": [], "top_score": top_score}
        return {"status": "out_of_scope", "relevant_results": [], "top_score": top_score}

    # Obvious off-topic + weak top score → out of scope even if something squeaked through.
    if obviously_off and top_score is not None and top_score < threshold + 1.0:
        return {"status": "out_of_scope", "relevant_results": [], "top_score": top_score}

    # MH-related query but only weakly supported evidence.
    insufficient_cutoff = (
        INSUFFICIENT_EVIDENCE_THRESHOLD if USE_RERANKING else FUSED_RELEVANCE_THRESHOLD * 0.6
    )
    if top_score is not None and top_score < insufficient_cutoff + (threshold - insufficient_cutoff) * 0.35:
        if has_mh_signal and not obviously_off:
            return {"status": "insufficient", "relevant_results": relevant, "top_score": top_score}

    return {"status": "supported", "relevant_results": relevant, "top_score": top_score}
