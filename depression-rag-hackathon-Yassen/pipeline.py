"""
Orchestration layer. This is what main.py and api.py call.

ask() ties retrieval, relevance gating, generation, citation validation,
and confidence scoring into one structured response.
"""

from ingest import (
    build_chunks_and_metadata, embed_chunks, build_bm25_index, get_chroma_collection,
    corpus_cache_exists, save_corpus_cache, load_corpus_cache,
    save_bm25_cache, load_bm25_cache,
)
from retrieval import hybrid_search
from generation import generate_answer
from relevance import (
    classify_retrieval,
    OUT_OF_SCOPE_MESSAGE,
    INSUFFICIENT_EVIDENCE_MESSAGE,
)
from citations import (
    assign_citation_ids,
    validate_and_clean_citations,
    filter_cited_sources,
    uncited_results,
    result_to_source,
)
from confidence import compute_confidence


def load_or_build_index(force_rebuild=False):
    """
    Returns (collection, bm25_index, chunk_texts, chunk_ids, metadata_list).
    Loads from disk cache unless force_rebuild=True or the cache is missing.
    """
    if not force_rebuild and corpus_cache_exists():
        print("Loading cached corpus + BM25 index from disk (skipping re-ingestion)...")
        chunk_texts, chunk_ids, metadata_list = load_corpus_cache()
        bm25_index = load_bm25_cache()
        collection = get_chroma_collection()
        print(f"Loaded {len(chunk_texts)} chunks.")
        return collection, bm25_index, chunk_texts, chunk_ids, metadata_list

    print("No cache found (or --rebuild requested) — running full ingestion...")
    chunk_texts, chunk_ids, metadata_list = build_chunks_and_metadata()

    if not chunk_texts:
        raise RuntimeError(
            "No chunks were produced — check that PDFs exist in the pdfs/ folder."
        )

    collection = embed_chunks(chunk_texts, chunk_ids, metadata_list)
    bm25_index = build_bm25_index(chunk_texts)

    save_corpus_cache(chunk_texts, chunk_ids, metadata_list)
    save_bm25_cache(bm25_index)

    return collection, bm25_index, chunk_texts, chunk_ids, metadata_list


def _empty_response(status: str, message: str) -> dict:
    return {
        "answer": message,
        "confidence": 0.0,
        "status": status,
        "sources": [],
        "additional_sources": [],
        "results": [],
    }


def ask(index, query, n_results=5, **search_kwargs) -> dict:
    """
    End-to-end RAG: retrieve → relevance gate → generate → validate citations → score.

    Returns a dict with answer, confidence, sources, additional_sources, status, results.
    """
    collection, bm25_index, chunk_texts, chunk_ids, metadata_list = index

    raw_results = hybrid_search(
        collection, bm25_index, chunk_texts, chunk_ids, metadata_list,
        query, n_results=n_results, verbose=False, **search_kwargs,
    )

    classification = classify_retrieval(query, raw_results)
    status = classification["status"]
    relevant_results = classification["relevant_results"]

    if status == "out_of_scope":
        return _empty_response("out_of_scope", OUT_OF_SCOPE_MESSAGE)

    numbered = assign_citation_ids(relevant_results)
    valid_id_set = {r["citation_id"] for r in numbered}

    if status == "insufficient":
        return {
            "answer": INSUFFICIENT_EVIDENCE_MESSAGE,
            "confidence": compute_confidence(
                status=status,
                relevant_results=numbered,
                cited_results=[],
                answer=INSUFFICIENT_EVIDENCE_MESSAGE,
                valid_citation_ids=set(),
            ),
            "status": "insufficient",
            "sources": [],
            "additional_sources": [],
            "results": [],
        }

    answer = generate_answer(query, numbered)
    if not answer.strip():
        return _empty_response("insufficient", INSUFFICIENT_EVIDENCE_MESSAGE)

    cleaned_answer, used_ids = validate_and_clean_citations(answer, valid_id_set)
    cited_chunks = filter_cited_sources(numbered, used_ids)
    additional = uncited_results(numbered, used_ids)

    if not cited_chunks and numbered:
        # LLM/extractive produced no valid citations — fall back to top chunk.
        top = numbered[0]
        snippet = top.get("text", "")[:500].strip()
        if snippet:
            cleaned_answer = f"{snippet} [1]"
            used_ids = {1}
            cited_chunks = [top]
            additional = numbered[1:]

    confidence = compute_confidence(
        status="supported",
        relevant_results=numbered,
        cited_results=cited_chunks,
        answer=cleaned_answer,
        valid_citation_ids=used_ids,
    )

    return {
        "answer": cleaned_answer,
        "confidence": confidence,
        "status": "supported",
        "sources": [result_to_source(r) for r in cited_chunks],
        "additional_sources": [result_to_source(r) for r in additional],
        "results": cited_chunks,
    }
