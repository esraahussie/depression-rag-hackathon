"""
Covers:
  - Step 1: the strict system prompt (safety contract between retrieval
    and generation).
  - Step 2: the structured answer schema (Recommendation, Supporting
    Evidence, Citations, Confidence & Safety).

Not covered here (left for the next part / teammates, per Day3.pptx):
  - Step 3: richer citation formatting polish.
  - Step 4: explicit claim-to-evidence linking/verification.
  - Step 5: refusal threshold gating tuned on eval_set.json.
  - Step 6: confidence-label calibration against retrieval quality.

This plugs into the retrieval already built in main.py (Chroma
collection populated by `python main.py`). It works two ways:

  - If GROQ_API_KEY is set: calls a Groq-hosted model with the
    grounding prompt and parses its structured JSON response.
  - If not: falls back to a deterministic extractive generator that
    builds the same schema directly from retrieved chunk text, so the
    schema and prompt can be tested and demoed with zero API setup.
"""

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

ANSWER SCHEMA:
{
  "recommendation": "<short, direct answer based only on retrieved chunks; null if insufficient evidence>",
  "supporting_evidence": [
    {
      "chunk_id": "<string>",
      "excerpt": "<short excerpt from that chunk, used to support the recommendation>"
    }
  ],
  "citations": [
    {
      "document_name": "<string>",
      "section_title": "<string>",
      "page": "<string, e.g. '18' or '18-19'>",
      "chunk_id": "<string>",
      "source_url": "<string, empty if unavailable>",
      "retrieval_score": <float>
    }
  ],
  "confidence": "<High|Medium|Low|Insufficient Evidence>",
  "disclaimer": "This is guideline-derived support information, not a substitute for clinical judgment."
}
"""

CONFIDENCE_LABELS = ("High", "Medium", "Low", "Insufficient Evidence")


def _get_collection():
    import chromadb
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)


def retrieve_context(query, k=5, min_score=MIN_RETRIEVE_SCORE):
    """Top-k retrieval via the existing Chroma index. Returns a list of
    hits with text + metadata + similarity, already gated by
    min_score (same gate as Day 2, so generation never sees evidence
    that retrieval itself would have refused)."""
    collection = _get_collection()
    cleaned = clean_query(query)
    results = collection.query(query_texts=[cleaned], n_results=k)

    hits = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for text, meta, distance in zip(documents, metadatas, distances):
        similarity = 1 - distance
        if similarity < min_score:
            continue
        hits.append({"text": text, "similarity": round(float(similarity), 4), **meta})

    return hits



def format_context_for_prompt(hits):
    """One block per chunk, labeled with everything needed for citations
    (Step 3's "minimum citation" fields, plus chunk_id for traceability)."""
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


def citation_from_hit(hit):
    page = hit.get("page_start")
    page_end = hit.get("page_end")
    page_str = str(page) if page == page_end else f"{page}-{page_end}"
    return {
        "document_name": hit.get("source_file"),
        "section_title": hit.get("section_title"),
        "page": page_str,
        "chunk_id": hit.get("chunk_id"),
        "source_url": hit.get("source_url") or "",
        "retrieval_score": hit.get("similarity"),
    }


def confidence_from_hits(hits):
    """Confidence reflects retrieval quality, not model self-belief
    (slide 11) - it's derived from the similarity scores already
    computed by retrieval, using the same 0.53 gate Day 2 established."""
    if not hits:
        return "Insufficient Evidence"
    top = hits[0]["similarity"]
    if top >= 0.75:
        return "High"
    if top >= 0.65:
        return "Medium"
    return "Low"



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
        # Groq supports OpenAI-style JSON mode for models that allow it;
        # we still defensively parse/strip below in case a model ignores it.
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()
    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _best_sentence(query, text):
    """Pick the sentence from a chunk with the most query-word overlap.
    Purely extractive - never invents wording, only selects existing text."""
    query_words = set(re.findall(r"[a-z]{3,}", query.lower()))
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    best, best_score = sentences[0] if sentences else text, -1
    for s in sentences:
        words = set(re.findall(r"[a-z]{3,}", s.lower()))
        score = len(words & query_words)
        if score > best_score:
            best, best_score = s, score
    return best.strip()


def extractive_answer(query, hits):
    if not hits:
        return {
            "recommendation": None,
            "supporting_evidence": [],
            "citations": [],
            "confidence": "Insufficient Evidence",
            "disclaimer": "This is guideline-derived support information, not a substitute for clinical judgment.",
        }

    top_hits = hits[:3]
    recommendation = " ".join(_best_sentence(query, h["text"]) for h in top_hits[:2])

    return{
        "recommendation": recommendation,
        "supporting_evidence": [
            {"chunk_id": h.get("chunk_id"), "excerpt": h["text"][:280]} for h in top_hits
        ],
        "citations": [citation_from_hit(h) for h in top_hits],
        "confidence": confidence_from_hits(hits),
        "disclaimer": "This is guideline-derived support information, not a substitute for clinical judgment.",
    }



def generate_answer(query, k=5, use_llm=None):
    """use_llm=None -> auto (use Groq if GROQ_API_KEY is set,
    otherwise the extractive fallback). Pass True/False to force one path."""
    hits = retrieve_context(query, k=k)

    if use_llm is None:
        use_llm = bool(os.environ.get("GROQ_API_KEY"))

    answer = None
    if use_llm:
        answer = call_llm(query, hits)

    if answer is None:
        answer = extractive_answer(query, hits)
        answer["_generation_method"] = "extractive_fallback"
    else:
        answer["_generation_method"] = "llm"

    answer["query"] = query
    answer["n_hits"] = len(hits)
    return answer


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    test_queries = [
        "What are the core diagnostic symptoms of major depressive disorder?",
        "What treatment options are effective for depression, including medication and therapy?",
        "What insulin dose should be started in a newly diagnosed adult with type 1 diabetes?",
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