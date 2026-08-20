"""
STEP 7: HYBRID SEARCH (keyword + semantic, each filtered, then merged)
STEP 8: RERANKING (cross-encoder, applied after fusion)

Architecture:
  Retriever
    -> Keyword Search  -> top N candidates -> Metadata Filter -> filtered list
    -> Semantic Search -> top N candidates -> Metadata Filter -> filtered list
  -> Merge + dedupe both filtered lists (reciprocal rank fusion)
  -> Rerank the fused candidates with a cross-encoder
  -> [optional] drop anything below the relevance threshold
  -> Return the top_k most relevant documents
"""

import re

from sentence_transformers import CrossEncoder

from settings import (
    HYBRID_CANDIDATE_POOL, RRF_K, USE_RERANKING, RERANK_MODEL, RERANK_POOL,
    RERANK_RELEVANCE_THRESHOLD,
)


# ---------------------------------------------------------------------
# Keyword search (BM25)
# ---------------------------------------------------------------------

def simple_tokenize(text):
    """Lowercase words only — good enough for BM25 keyword matching."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25_top_ids(bm25_index, chunk_ids, query, top_n):
    """Return chunk_ids ranked by keyword (BM25) score, best first."""
    tokenized_query = simple_tokenize(query)
    scores = bm25_index.get_scores(tokenized_query)
    ranked_positions = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [chunk_ids[i] for i in ranked_positions[:top_n]]


# ---------------------------------------------------------------------
# Semantic search (Chroma)
# ---------------------------------------------------------------------

def semantic_top_ids(collection, query, top_n):
    """Return chunk_ids ranked by semantic (embedding) similarity, best first."""
    results = collection.query(query_texts=[query], n_results=top_n)
    return results["ids"][0]


# ---------------------------------------------------------------------
# Metadata filter
# ---------------------------------------------------------------------

def passes_metadata_filter(metadata, source_filter=None, min_page=None, max_page=None):
    if source_filter is not None and metadata.get("source_file") not in source_filter:
        return False
    if min_page is not None and metadata.get("page_number", 0) < min_page:
        return False
    if max_page is not None and metadata.get("page_number", 0) > max_page:
        return False
    return True


def apply_metadata_filter(ranked_ids, id_to_meta, source_filter=None, min_page=None, max_page=None):
    return [
        doc_id for doc_id in ranked_ids
        if passes_metadata_filter(id_to_meta.get(doc_id, {}), source_filter, min_page, max_page)
    ]


# ---------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------

def reciprocal_rank_fusion(ranked_id_lists, k=RRF_K):
    """
    Merge several ranked lists of ids into one fused ranking. Each id gets
    1/(k + rank) points from each list it appears in, so a chunk found by
    BOTH keyword and semantic search naturally rises above one only one
    method found.
    """
    scores = {}
    for ranked_ids in ranked_id_lists:
        for rank, doc_id in enumerate(ranked_ids):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


# ---------------------------------------------------------------------
# Reranking (cross-encoder)
# ---------------------------------------------------------------------

_reranker_model = None  # loaded once and reused


def get_reranker_model(model_name=RERANK_MODEL):
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = CrossEncoder(model_name)
    return _reranker_model


def rerank_candidates(query, candidates, top_k):
    """
    candidates: list of result dicts (must have a "text" key). Scores each
    candidate against the query with a cross-encoder and returns the best
    top_k, sorted best-first, with a "rerank_score" added.
    """
    if not candidates:
        return []

    model = get_reranker_model()
    pairs = [[query, c["text"]] for c in candidates]
    scores = model.predict(pairs)

    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = float(score)

    reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return reranked[:top_k]


def apply_relevance_gate(results, threshold=RERANK_RELEVANCE_THRESHOLD):
    """
    Drop any result whose rerank_score falls below the threshold — the
    "no relevant information found" mechanism for out-of-scope queries.
    Only works when reranking is enabled.
    """
    return [r for r in results if r.get("rerank_score", float("-inf")) >= threshold]


# ---------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------

def hybrid_search(collection, bm25_index, chunk_texts, chunk_ids, metadata_list, query,
                   n_results=3, candidate_pool=HYBRID_CANDIDATE_POOL, rerank_pool=RERANK_POOL,
                   source_filter=None, min_page=None, max_page=None,
                   use_reranking=USE_RERANKING,
                   use_relevance_gate=False, relevance_threshold=RERANK_RELEVANCE_THRESHOLD,
                   verbose=True):
    """
    keyword search + semantic search (wide candidate pool)
      -> metadata filter, applied separately to each branch
      -> merge + dedupe (reciprocal rank fusion)
      -> rerank the fused candidates with a cross-encoder
      -> [optional] drop anything below the relevance threshold
      -> return top_k most relevant documents
    """
    id_to_text = dict(zip(chunk_ids, chunk_texts))
    id_to_meta = dict(zip(chunk_ids, metadata_list))

    keyword_candidates = bm25_top_ids(bm25_index, chunk_ids, query, candidate_pool)
    semantic_candidates = semantic_top_ids(collection, query, candidate_pool)

    keyword_filtered = apply_metadata_filter(keyword_candidates, id_to_meta, source_filter, min_page, max_page)
    semantic_filtered = apply_metadata_filter(semantic_candidates, id_to_meta, source_filter, min_page, max_page)

    if verbose:
        print(f"  keyword search:  {len(keyword_candidates)} candidates -> {len(keyword_filtered)} after metadata filter")
        print(f"  semantic search: {len(semantic_candidates)} candidates -> {len(semantic_filtered)} after metadata filter")

    keep = rerank_pool if use_reranking else n_results
    fused_ranking = reciprocal_rank_fusion([keyword_filtered, semantic_filtered])[:keep]

    candidates = []
    for doc_id, fused_score in fused_ranking:
        matched_by = []
        if doc_id in semantic_filtered:
            matched_by.append("semantic")
        if doc_id in keyword_filtered:
            matched_by.append("keyword")

        candidates.append({
            "chunk_id": doc_id,
            "fused_score": fused_score,
            "matched_by": "+".join(matched_by),
            "text": id_to_text.get(doc_id, ""),
            "metadata": id_to_meta.get(doc_id, {}),
        })

    if not use_reranking:
        return candidates[:n_results]

    results = rerank_candidates(query, candidates, n_results)

    if use_relevance_gate:
        results = apply_relevance_gate(results, relevance_threshold)

    return results
