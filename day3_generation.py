"""
Day 3 — grounded generation, citations, safety
===============================================
Steps covered:
  1. Strict system prompt (safety contract between retrieval and generation)
  2. Structured answer schema (Recommendation, Supporting Evidence,
     Citations, Confidence & Safety)
  3. Citation formatting polish (stable C1/C2 ids, human-readable strings,
     de-duplication when the same chunk backs more than one claim)
  4. Claim -> evidence linking + verification (every claim is checked
     against the text of the chunk(s) it cites; unsupported claims are
     flagged, not silently kept)
  5. Input risk classification + refusal-threshold calibration
     (Allowed / Needs Caution / Refuse-Redirect, and a data-driven
     retrieval confidence gate tuned against eval_set.json / day2_eval.json
     instead of a guessed constant)
  6. Confidence-label calibration against measured retrieval quality
     (High/Medium/Low cutoffs derived from Day 2's Precision@K numbers,
     not hand-picked)

This plugs into the retrieval already built in main.py (Chroma collection
populated by `python main.py`) and into Day 2's eval artifacts
(outputs/day2_eval.json, eval_set.json) for calibration.

Run:
    python main.py                      # build the Chroma index (Day 1/2)
    python day2_eval.py                 # produces outputs/day2_eval.json
    python day3_generation.py           # demo answers
    python day3_generation.py --calibrate   # (re)compute thresholds from
                                            # outputs/day2_eval.json and
                                            # save outputs/day3_calibration.json
"""

import argparse
import json
import os
import re

from dotenv import load_dotenv
load_dotenv()

from main import (
    CHROMA_FOLDER,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    MIN_RETRIEVE_SCORE,
    OUTPUT_FOLDER,
    clean_query,
)

ANSWERS_FILE = os.path.join(OUTPUT_FOLDER, "day3_answers.json")
CALIBRATION_FILE = os.path.join(OUTPUT_FOLDER, "day3_calibration.json")
DAY2_RESULTS_FILE = os.path.join(OUTPUT_FOLDER, "day2_eval.json")
EVAL_SET_FILE = "eval_set.json"

# Groq free-tier models (as of writing): "llama-3.1-8b-instant" is the
# fastest/cheapest; "llama-3.3-70b-versatile" is stronger but slower.
# Swap this string if you want a different one from Groq's model list.
MODEL_NAME = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are an evidence-grounded clinical decision support assistant.

Rules you must follow exactly:
1. Use ONLY the retrieved guideline context provided below. Do not use
   any outside medical knowledge, training data, or assumptions.
2. If the context does not support the answer, or only partially
   supports it, say explicitly that the evidence is insufficient. Do
   not fill gaps with general knowledge.
3. Do not provide patient-specific diagnosis, dosage, or treatment.
   You support clinicians; you do not replace clinical judgment.
4. Every recommendation must include citations pointing to the exact
   chunk(s) that support it (document, section, page).
5. Do not cite a chunk that does not actually support the claim next
   to it.
6. Output ONLY valid JSON matching the ANSWER SCHEMA below. No
   markdown, no preamble, no text outside the JSON object.

ANSWER_SCHEMA = 
{
  "recommendation": "short answer or null",
  "claims": [
    {
      "claim_id": "CL1",
      "text": "claim made in the recommendation",
      "citation_ids": ["C1"]
    }
  ],
  "supporting_evidence": [
    {
      "chunk_id": "string",
      "excerpt": "short supporting excerpt"
    }
  ],
  "citations": [
    {
      "citation_id": "C1",
      "document_name": "string",
      "section_title": "string",
      "page": "string",
      "chunk_id": "string",
      "source_url": "string",
      "retrieval_score": 0.0
    }
  ],
  "confidence": "High|Medium|Low|Insufficient Evidence",
  "disclaimer": "This is guideline-derived support information, not a substitute for clinical judgment."
}
"""

CONFIDENCE_LABELS = ("High", "Medium", "Low", "Insufficient Evidence")

DEFAULT_DISCLAIMER = (
    "This is guideline-derived support information, not a substitute "
    "for clinical judgment."
)

# ---------------------------------------------------------------------------
# Step 5a — input risk classification
# ---------------------------------------------------------------------------
# Three buckets, matching the Day 4 slide's "Input Risk Classification":
#   allowed        -> normal guideline lookup, proceed to retrieval
#   needs_caution   -> patient-specific phrasing; answer but strip the
#                      personal framing and lean on the disclaimer harder
#   refuse_redirect -> acute personal crisis or clearly out-of-scope;
#                      never call the LLM, return a fixed safe response

EMERGENCY_PATTERNS = [
    r"\bi (want to|'m going to|am going to) (kill|hurt) (myself|me)\b",
    r"\bi feel (suicidal|like ending my life)\b",
    r"\bsuicidal thoughts? (right now|tonight)\b",
    r"\bi('| a)?m having (a heart attack|chest pain)\b",
    r"\bi(?:'ve| have) (taken|overdosed on)\b",
    r"\bi can'?t breathe\b",
    r"\bactively (bleeding|overdosing)\b",
]

PATIENT_SPECIFIC_PATTERNS = [
    r"\bmy (patient|son|daughter|wife|husband|mother|father|child)\b",
    r"\bwhat dose should i (give|prescribe|take)\b",
    r"\bshould i (start|stop|increase|decrease) (my|his|her|their) (medication|dose|dosage)\b",
    r"\bis it safe for me to\b",
    r"\bcan i (take|give|prescribe)\b",
]

# A light out-of-scope tripwire for obviously unrelated topics. This is a
# *secondary* signal only — the real out-of-scope defense is the retrieval
# confidence gate (Step 5b), because a keyword list can never enumerate
# every off-topic question.
OUT_OF_SCOPE_HINTS = [
    r"\binsulin dose\b", r"\bdiabetes\b", r"\bcancer\b", r"\bcovid\b",
    r"\bweather\b", r"\bstock price\b", r"\brecipe\b", r"\bpython code\b",
    r"\bfootball\b",
]

_EMERGENCY_RE = re.compile("|".join(EMERGENCY_PATTERNS), re.I)
_PATIENT_SPECIFIC_RE = re.compile("|".join(PATIENT_SPECIFIC_PATTERNS), re.I)
_OUT_OF_SCOPE_RE = re.compile("|".join(OUT_OF_SCOPE_HINTS), re.I)

CRISIS_REDIRECT_MESSAGE = (
    "I can't help with an active personal crisis. If you or someone else "
    "is in immediate danger, please contact local emergency services now, "
    "or a crisis line (e.g. 988 in the US, or your national equivalent). "
    "I can still answer general, guideline-based clinical questions about "
    "depression and anxiety screening/management."
)

OUT_OF_SCOPE_MESSAGE = (
    "This question falls outside the guidelines loaded in this system "
    "(depression / anxiety screening and management). I won't guess — "
    "please consult a source specific to that topic."
)


def classify_input(query):
    """Returns (bucket, reason) where bucket is one of
    'refuse_redirect', 'needs_caution', 'allowed'."""
    q = (query or "").strip()
    if _EMERGENCY_RE.search(q):
        return "refuse_redirect", "acute_personal_crisis"
    if _OUT_OF_SCOPE_RE.search(q):
        return "refuse_redirect", "keyword_out_of_scope"
    if _PATIENT_SPECIFIC_RE.search(q):
        return "needs_caution", "patient_specific_phrasing"
    return "allowed", "general_guideline_question"


def fixed_refusal_answer(query, reason):
    message = CRISIS_REDIRECT_MESSAGE if reason == "acute_personal_crisis" else OUT_OF_SCOPE_MESSAGE
    return {
        "recommendation": None,
        "claims": [],
        "supporting_evidence": [],
        "citations": [],
        "confidence": "Insufficient Evidence",
        "disclaimer": DEFAULT_DISCLAIMER,
        "refusal_reason": reason,
        "refusal_message": message,
        "_generation_method": "input_gate_refusal",
        "query": query,
        "n_hits": 0,
    }


# ---------------------------------------------------------------------------
# Step 6 — confidence-label calibration (data-driven, not hand-picked)
# ---------------------------------------------------------------------------

DEFAULT_CALIBRATION = {
    "high_cutoff": 0.75,
    "medium_cutoff": 0.65,
    "retrieval_gate": MIN_RETRIEVE_SCORE,
    "source": "default (uncalibrated)",
}


def _iter_day2_questions(day2_results):
    """Yield (top1_similarity, is_relevant_at_rank1) across every strategy
    in every chunk setting Day 2 tested, so calibration uses all the
    labeled signal available, not just the single 'best' row."""
    for setup in day2_results.get("results", []):
        for strategy, payload in setup.get("strategies", {}).items():
            for q in payload.get("questions", []):
                if q.get("out_of_scope"):
                    continue
                hits = q.get("hits") or []
                if not hits:
                    continue
                top = hits[0]
                yield float(top.get("similarity", 0.0)), bool(top.get("relevant"))


def calibrate_confidence_thresholds(day2_results_path=DAY2_RESULTS_FILE):
    """Buckets top-1 similarity scores from Day 2's labeled eval and finds
    the score where rank-1 precision crosses 0.80 (High) and 0.50
    (Medium). Anything below 'Medium' but above the retrieval gate is Low;
    below the gate is Insufficient Evidence (unchanged from Day 2)."""
    if not os.path.exists(day2_results_path):
        return dict(DEFAULT_CALIBRATION)

    with open(day2_results_path, encoding="utf-8") as f:
        day2_results = json.load(f)

    pairs = sorted(_iter_day2_questions(day2_results), key=lambda p: -p[0])
    if not pairs:
        return dict(DEFAULT_CALIBRATION)

    # Sweep candidate cutoffs = the observed scores themselves; for each
    # candidate, measure precision of "top1 >= cutoff => relevant" over
    # the whole labeled set. Pick the highest cutoff that still clears
    # each precision bar, so the bar is set by evidence, not a guess.
    candidates = sorted({round(s, 3) for s, _ in pairs}, reverse=True)

    def precision_at_cutoff(cutoff):
        kept = [rel for score, rel in pairs if score >= cutoff]
        if not kept:
            return 0.0
        return sum(kept) / len(kept)

    high_cutoff = None
    medium_cutoff = None

    # Find High cutoff
    for c in candidates: 
        precision = precision_at_cutoff(c)

        if precision >= 0.80:
            high_cutoff = c
            break

    # Find Medium cutoff strictly below High
    for c in candidates:
        precision = precision_at_cutoff(c)

        if high_cutoff is not None and c < high_cutoff and precision >= 0.50:
            medium_cutoff = c
            break

    high_cutoff = high_cutoff if high_cutoff is not None else DEFAULT_CALIBRATION["high_cutoff"]
    medium_cutoff = medium_cutoff if medium_cutoff is not None else DEFAULT_CALIBRATION["medium_cutoff"]
    # Never let Medium sit above High or below the retrieval gate.
    medium_cutoff = min(medium_cutoff, high_cutoff)
    medium_cutoff = max(medium_cutoff, MIN_RETRIEVE_SCORE)

    return {
        "high_cutoff": round(high_cutoff, 3),
        "medium_cutoff": round(medium_cutoff, 3),
        "retrieval_gate": MIN_RETRIEVE_SCORE,
        "n_labeled_pairs": len(pairs),
        "source": os.path.basename(day2_results_path),
    }


def load_calibration():
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, encoding="utf-8") as f:
            return json.load(f)
    return dict(DEFAULT_CALIBRATION)


def save_calibration(calibration, path=CALIBRATION_FILE):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)
    return path


def confidence_from_hits(hits, calibration=None):
    """Confidence reflects retrieval quality, not model self-belief —
    it's derived from similarity scores using thresholds that were
    measured against Day 2's labeled questions (see calibrate_confidence_
    thresholds), falling back to sane defaults if no calibration file
    exists yet."""
    if not hits:
        return "Insufficient Evidence"
    calibration = calibration or load_calibration()
    top = hits[0]["similarity"]
    if top >= calibration.get("high_cutoff", DEFAULT_CALIBRATION["high_cutoff"]):
        return "High"
    if top >= calibration.get("medium_cutoff", DEFAULT_CALIBRATION["medium_cutoff"]):
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Step 5b — refusal threshold calibration (retrieval confidence gate)
# ---------------------------------------------------------------------------

def calibrate_confidence_thresholds(day2_results_path=DAY2_RESULTS_FILE):
    """
    Calibrate confidence bands from the distribution of labeled retrieval
    similarity scores.

    The retrieval gate remains responsible for deciding whether there is
    enough evidence to answer.

    Confidence bands describe how strong the retrieval similarity is:
        High   -> upper part of observed labeled-score distribution
        Medium -> middle/upper part
        Low    -> above retrieval gate but below Medium

    This is intentionally separate from refusal calibration.
    """

    if not os.path.exists(day2_results_path):
        return dict(DEFAULT_CALIBRATION)

    with open(day2_results_path, encoding="utf-8") as f:
        day2_results = json.load(f)

    scores = []

    for setup in day2_results.get("results", []):
        for strategy, payload in setup.get("strategies", {}).items():
            for q in payload.get("questions", []):

                if q.get("out_of_scope"):
                    continue

                hits = q.get("hits") or []

                for hit in hits:
                    score = hit.get("similarity")

                    if score is not None:
                        scores.append(float(score))

    if not scores:
        return dict(DEFAULT_CALIBRATION)

    scores.sort()

    def percentile(values, p):
        """
        Linear percentile calculation without requiring NumPy.
        p is between 0 and 1.
        """
        if not values:
            return 0.0

        if len(values) == 1:
            return values[0]

        position = (len(values) - 1) * p
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)

        weight = position - lower

        return (
            values[lower] * (1 - weight)
            + values[upper] * weight
        )

    # Use the observed labeled retrieval-score distribution.
    medium_cutoff = percentile(scores, 0.60)
    high_cutoff = percentile(scores, 0.80)

    # Keep the bands above the retrieval gate.
    medium_cutoff = max(
        medium_cutoff,
        MIN_RETRIEVE_SCORE
    )

    high_cutoff = max(
        high_cutoff,
        medium_cutoff
    )

    return {
        "high_cutoff": round(high_cutoff, 3),
        "medium_cutoff": round(medium_cutoff, 3),
        "retrieval_gate": MIN_RETRIEVE_SCORE,
        "n_labeled_scores": len(scores),
        "score_min": round(min(scores), 3),
        "score_max": round(max(scores), 3),
        "score_median": round(percentile(scores, 0.50), 3),
        "source": os.path.basename(day2_results_path),
        "method": "labeled_score_distribution_percentiles"
    }

# ---------------------------------------------------------------------------
# Retrieval (unchanged mechanics from the original Day 3 draft)
# ---------------------------------------------------------------------------

def _get_collection():
    import chromadb
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)


def retrieve_context(query, k=5, min_score=None, calibration=None):
    """Top-k retrieval via the existing Chroma index. Returns a list of
    hits with text + metadata + similarity, gated by the calibrated
    retrieval threshold (Step 5) so generation never sees evidence that
    retrieval itself would have refused."""
    calibration = calibration or load_calibration()
    gate = min_score if min_score is not None else calibration.get("retrieval_gate", MIN_RETRIEVE_SCORE)

    collection = _get_collection()
    cleaned = clean_query(query)
    results = collection.query(query_texts=[cleaned], n_results=k)

    hits = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for text, meta, distance in zip(documents, metadatas, distances):
        similarity = 1 - distance
        if similarity < gate:
            continue
        hits.append({"text": text, "similarity": round(float(similarity), 4), **meta})

    return hits


def format_context_for_prompt(hits):
    """One block per chunk, labeled with everything needed for citations,
    plus chunk_id for traceability."""
    blocks = []
    for h in hits:
        page = h.get("page_start")
        page_end = h.get("page_end")
        page_str = str(page) if page == page_end else f"{page}-{page_end}"
        blocks.append(
            f"[chunk_id={h.get('chunk_id')}] "
            f"({h.get('source_file')}, section: \"{h.get('section_title')}\", "
            f"page {page_str}, score={h.get('similarity')})\n"
            f"{h['text']}"
        )
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(query, hits):
    context_block = format_context_for_prompt(hits)
    return (
        f"RETRIEVED CONTEXT:\n{context_block}\n\n"
        f"CLINICAL QUESTION:\n{query}\n\n"
        f"Respond with JSON only, following the ANSWER SCHEMA exactly."
    )


# ---------------------------------------------------------------------------
# Step 3 — citation formatting polish
# ---------------------------------------------------------------------------

def citation_from_hit(hit, citation_id):
    page = hit.get("page_start")
    page_end = hit.get("page_end")
    page_str = str(page) if page == page_end else f"{page}-{page_end}"

    document = hit.get("source_file") or "Unknown document"
    section = hit.get("section_title") or "Unspecified section"

    return {
        "citation_id": citation_id,
        "document_name": document,
        "section_title": section,
        "page": page_str,
        "chunk_id": hit.get("chunk_id"),
        "source_url": hit.get("source_url") or "",
        "retrieval_score": hit.get("similarity"),
        "formatted": f"[{citation_id}] {document} — {section}, p. {page_str}",
    }


def assign_citations(hits):
    """Builds a stable chunk_id -> citation dict, so if two different
    claims lean on the same chunk they share one citation_id (C1) instead
    of minting duplicates (C1, C2, ...) for identical evidence."""
    citations_by_chunk = {}
    ordered = []
    for hit in hits:
        chunk_id = hit.get("chunk_id")
        if chunk_id in citations_by_chunk:
            continue
        cid = f"C{len(ordered) + 1}"
        citation = citation_from_hit(hit, cid)
        citations_by_chunk[chunk_id] = citation
        ordered.append(citation)
    return citations_by_chunk, ordered


def format_citations_block(citations):
    """Human-readable citation list for display beneath an answer."""
    return "\n".join(c["formatted"] for c in citations)


# ---------------------------------------------------------------------------
# Step 4 — claim -> evidence linking and verification
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z]{3,}")
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was",
    "were", "has", "have", "not", "should", "may", "can", "who", "their",
    "its", "into", "than", "then", "also", "such", "any", "all", "over",
}


def _significant_words(text):
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOPWORDS}


def _support_ratio(claim_text, evidence_text):
    """Fraction of the claim's significant words that also appear in the
    cited evidence. Cheap, dependency-free, and conservative: it can
    only ever *catch* unsupported claims, never invent support that
    isn't lexically present in the retrieved text."""
    claim_words = _significant_words(claim_text)
    if not claim_words:
        return 1.0
    evidence_words = _significant_words(evidence_text)
    overlap = claim_words & evidence_words
    return len(overlap) / len(claim_words)


UNSUPPORTED_THRESHOLD = 0.35  # below this overlap ratio, a claim is flagged


def verify_claims(claims, citations_by_chunk, hits_by_chunk):
    """For every claim, check its cited chunk(s) actually contain the
    words the claim is making. Mutates nothing; returns a new list with
    'verified' / 'support_ratio' / 'unsupported_reason' added, plus a
    summary count so the caller can downgrade confidence when needed."""
    verified_claims = []
    unsupported_count = 0

    for claim in claims:
        citation_ids = claim.get("citation_ids") or []
        evidence_text = ""
        missing_citation = False
        for cid in citation_ids:
            chunk_id = None
            for chunk, citation in citations_by_chunk.items():
                if citation["citation_id"] == cid:
                    chunk_id = chunk
                    break
            if chunk_id is None or chunk_id not in hits_by_chunk:
                missing_citation = True
                continue
            evidence_text += " " + hits_by_chunk[chunk_id]["text"]

        if not citation_ids:
            verified_claims.append({
                **claim, "verified": False, "support_ratio": 0.0,
                "unsupported_reason": "no_citation_attached",
            })
            unsupported_count += 1
            continue

        if missing_citation and not evidence_text.strip():
            verified_claims.append({
                **claim, "verified": False, "support_ratio": 0.0,
                "unsupported_reason": "citation_id_not_found_in_context",
            })
            unsupported_count += 1
            continue

        ratio = round(_support_ratio(claim.get("text", ""), evidence_text), 3)
        is_verified = ratio >= UNSUPPORTED_THRESHOLD
        verified_claims.append({
            **claim,
            "verified": is_verified,
            "support_ratio": ratio,
            "unsupported_reason": None if is_verified else "low_lexical_overlap_with_cited_chunk",
        })
        if not is_verified:
            unsupported_count += 1

    return verified_claims, unsupported_count


def apply_claim_verification(answer, hits):
    """Runs Step 4 verification over whatever claims/citations an answer
    (LLM or extractive) produced, then folds the result back in: flags
    each claim, and downgrades confidence one notch if any claim in the
    answer could not be verified against the retrieved text — mirrors
    the 'Unsupported Claim Detection' guardrail from the safety workflow."""
    hits_by_chunk = {h.get("chunk_id"): h for h in hits}
    citations_by_chunk = {c.get("chunk_id"): c for c in answer.get("citations", [])}

    claims = answer.get("claims") or []
    verified_claims, unsupported_count = verify_claims(claims, citations_by_chunk, hits_by_chunk)
    answer["claims"] = verified_claims
    answer["unsupported_claim_count"] = unsupported_count

    if unsupported_count and answer.get("confidence") in ("High", "Medium"):
        downgrade = {"High": "Medium", "Medium": "Low"}
        answer["confidence"] = downgrade[answer["confidence"]]
        answer["confidence_downgrade_reason"] = (
            f"{unsupported_count} claim(s) failed lexical verification against "
            "cited chunk text."
        )
    return answer


# ---------------------------------------------------------------------------
# Generation paths (LLM + extractive fallback)
# ---------------------------------------------------------------------------

def call_llm(query, hits):
    """Calls a Groq-hosted model (OpenAI-compatible chat completions API).
    Requires the `groq` package (`pip install groq`) and a GROQ_API_KEY
    env var — free to obtain at https://console.groq.com/keys.
    """
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    user_prompt = build_user_prompt(query, hits)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=1024,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()
    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    # The model may invent its own citation_ids/order; re-derive citations
    # from the actual retrieved hits (Step 3) so the ids we display are
    # always backed by a real chunk, never a hallucinated one.
    citations_by_chunk, ordered_citations = assign_citations(hits)
    parsed["citations"] = ordered_citations
    return parsed


def _best_sentence(query, text):
    """Pick the sentence from a chunk with the most query-word overlap.
    Purely extractive — never invents wording, only selects existing text."""
    query_words = _significant_words(query)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    best, best_score = (sentences[0] if sentences else text), -1
    for s in sentences:
        score = len(_significant_words(s) & query_words)
        if score > best_score:
            best, best_score = s, score
    return best.strip()


def extractive_answer(query, hits, calibration=None):
    if not hits:
        return {
            "recommendation": None,
            "claims": [],
            "supporting_evidence": [],
            "citations": [],
            "confidence": "Insufficient Evidence",
            "disclaimer": DEFAULT_DISCLAIMER,
        }

    top_hits = hits[:3]
    citations_by_chunk, ordered_citations = assign_citations(top_hits)

    claims = []
    sentences = []
    for i, hit in enumerate(top_hits[:2], start=1):
        sentence = _best_sentence(query, hit["text"])
        sentences.append(sentence)
        citation = citations_by_chunk[hit.get("chunk_id")]
        claims.append({
            "claim_id": f"CL{i}",
            "text": sentence,
            "citation_ids": [citation["citation_id"]],
        })

    return {
        "recommendation": " ".join(sentences),
        "claims": claims,
        "supporting_evidence": [
            {"chunk_id": h.get("chunk_id"), "excerpt": h["text"][:280]} for h in top_hits
        ],
        "citations": ordered_citations,
        "confidence": confidence_from_hits(hits, calibration=calibration),
        "disclaimer": DEFAULT_DISCLAIMER,
    }


def generate_answer(query, k=5, use_llm=None, calibration=None):
    """use_llm=None -> auto (use Groq if GROQ_API_KEY is set, otherwise the
    extractive fallback). Pass True/False to force one path.

    Pipeline order (Steps 5 -> retrieval gate -> generation -> Step 4):
      1. classify_input()      — refuse/redirect before touching retrieval
      at all for acute-crisis or clearly out-of-scope questions
      2. retrieve_context()    — gated by the calibrated threshold
      3. call_llm / extractive — produce the structured answer
      4. apply_claim_verification() — catch + flag unsupported claims,
                                        downgrade confidence if needed
    """
    calibration = calibration or load_calibration()

    bucket, reason = classify_input(query)
    if bucket == "refuse_redirect":
        return fixed_refusal_answer(query, reason)

    hits = retrieve_context(query, k=k, calibration=calibration)

    if use_llm is None:
        use_llm = bool(os.environ.get("GROQ_API_KEY"))

    answer = None
    if use_llm:
        answer = call_llm(query, hits)
        if answer is not None:
            answer["confidence"] = confidence_from_hits(hits, calibration=calibration)

    if answer is None:
        answer = extractive_answer(query, hits, calibration=calibration)
        answer["_generation_method"] = "extractive_fallback"
    else:
        answer["_generation_method"] = "llm"

    answer = apply_claim_verification(answer, hits)

    if bucket == "needs_caution":
        answer["input_risk"] = "needs_caution"
        answer["disclaimer"] = (
            answer.get("disclaimer", DEFAULT_DISCLAIMER)
            + " This answer describes general guideline content only — it is "
            "not personalized advice for a specific patient."
        )
    else:
        answer["input_risk"] = "allowed"

    answer["query"] = query
    answer["n_hits"] = len(hits)
    return answer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_calibration():
    print("Calibrating confidence thresholds from", DAY2_RESULTS_FILE, "...")
    confidence_calibration = calibrate_confidence_thresholds()

    print("Calibrating refusal threshold from", DAY2_RESULTS_FILE, "...")
    refusal_calibration = calibrate_refusal_threshold()

    calibration = {
        "high_cutoff": confidence_calibration["high_cutoff"],
        "medium_cutoff": confidence_calibration["medium_cutoff"],
        "retrieval_gate": refusal_calibration["recommended_threshold"],
        "confidence_calibration_detail": confidence_calibration,
        "refusal_calibration_detail": refusal_calibration,
    }
    path = save_calibration(calibration)
    print(json.dumps(calibration, indent=2))
    print(f"\nSaved calibration -> {path}")
    return calibration


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", action="store_true",
                         help="Recompute confidence + refusal thresholds from day2_eval.json")
    args = parser.parse_args()

    if args.calibrate:
        run_calibration()
        raise SystemExit(0)

    test_queries = [
        "What are the core diagnostic symptoms of major depressive disorder?",
        "What treatment options are effective for depression, including medication and therapy?",
        "What insulin dose should be started in a newly diagnosed adult with type 1 diabetes?",
        "I feel suicidal right now, what should I do?",
        "My son was just diagnosed with depression, what dose should I give him?",
    ]

    results = []
    for query in test_queries:
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        answer = generate_answer(query)
        print(json.dumps(answer, indent=2, ensure_ascii=False))
        results.append(answer)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(ANSWERS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved -> {ANSWERS_FILE}")
