"""
STEP 10: EVALUATION — precision@k and recall@k

CAVEAT: proper precision/recall needs a full manual relevance judgment for
every chunk in the corpus. This is a practical PROXY instead: a retrieved
chunk counts as "relevant" if its source_file contains one of the query's
expected relevant_keywords — i.e. these numbers measure SOURCE-LEVEL
coverage, not true chunk-level relevance.
"""

from settings import TEST_QUERIES, EVAL_K_VALUES
from retrieval import hybrid_search
from citations import format_citation


def chunk_is_relevant(metadata, relevant_keywords):
    source = metadata.get("source_file", "").lower()
    return any(keyword.lower() in source for keyword in relevant_keywords)


def precision_at_k(retrieved_metadatas, relevant_keywords, k):
    """Of the top-k results, what fraction are relevant?"""
    top_k = retrieved_metadatas[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for m in top_k if chunk_is_relevant(m, relevant_keywords))
    return relevant_count / len(top_k)


def recall_at_k(retrieved_metadatas, relevant_keywords, k):
    """Of all EXPECTED relevant sources for this query, how many showed up
    somewhere in the top-k? (source-level recall — see caveat above)."""
    if not relevant_keywords:
        return None

    top_k = retrieved_metadatas[:k]
    sources_in_top_k = {m.get("source_file", "").lower() for m in top_k}
    sources_found = sum(
        1 for keyword in relevant_keywords
        if any(keyword.lower() in source for source in sources_in_top_k)
    )
    return sources_found / len(relevant_keywords)


def run_evaluation(collection, bm25_index, chunk_texts, chunk_ids, metadata_list,
                    queries=None, k_values=None,
                    use_relevance_gate=False, **search_kwargs):
    """
    Runs every test query, prints retrieved results (with rerank_score, so
    you can calibrate RERANK_RELEVANCE_THRESHOLD), and reports
    precision@k / recall@k. Out-of-scope queries (empty relevant_keywords)
    are reported separately.
    """
    queries = queries if queries is not None else TEST_QUERIES
    k_values = k_values if k_values is not None else EVAL_K_VALUES

    max_k = max(k_values)
    per_query_scores = []
    out_of_scope_hit_counts = []

    for query_entry in queries:
        query = query_entry["query"]
        relevant_keywords = query_entry["relevant_keywords"]

        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        if relevant_keywords:
            print(f"(expects relevant sources containing: {relevant_keywords})")
        else:
            print("(OUT OF SCOPE — no source in this corpus should be relevant)")

        results = hybrid_search(collection, bm25_index, chunk_texts, chunk_ids,
                                 metadata_list, query, n_results=max_k,
                                 use_relevance_gate=use_relevance_gate, **search_kwargs)
        retrieved_metadatas = [r["metadata"] for r in results]

        if not results:
            print("  -> NO RESULTS PASSED THE RELEVANCE GATE ('no relevant information found')")

        for rank, result in enumerate(results, start=1):
            meta = result["metadata"]
            is_relevant = chunk_is_relevant(meta, relevant_keywords) if relevant_keywords else False
            relevance_tag = "RELEVANT" if is_relevant else ("n/a" if not relevant_keywords else "not relevant")
            rerank_note = f" | rerank_score={result['rerank_score']:.3f}" if "rerank_score" in result else ""
            preview = result["text"][:150].replace("\n", " ")
            print(f"  [{rank}] {format_citation(meta)} | {relevance_tag}{rerank_note}")
            print(f"       {preview}...")

        if relevant_keywords:
            scores_this_query = {
                k: {"precision": precision_at_k(retrieved_metadatas, relevant_keywords, k),
                    "recall": recall_at_k(retrieved_metadatas, relevant_keywords, k)}
                for k in k_values
            }
            per_query_scores.append(scores_this_query)
            print("  Scores:", {k: f"P={v['precision']:.2f} R={v['recall']:.2f}" for k, v in scores_this_query.items()})
        else:
            out_of_scope_hit_counts.append(len(results))
            if results:
                print(f"  {len(results)} result(s) returned for an out-of-scope query "
                      f"(ideally this system would flag 'no relevant information found' instead)")
            else:
                print("  Correctly returned nothing for an out-of-scope query.")

    print("\n" + "#" * 80)
    print("# EVALUATION SUMMARY")
    print("#" * 80)

    print(f"\nOn-topic queries evaluated: {len(per_query_scores)}")
    for k in k_values:
        if per_query_scores:
            avg_precision = sum(s[k]["precision"] for s in per_query_scores) / len(per_query_scores)
            avg_recall = sum(s[k]["recall"] for s in per_query_scores) / len(per_query_scores)
            print(f"  Average Precision@{k}: {avg_precision:.3f}   Average Recall@{k}: {avg_recall:.3f}")

    if out_of_scope_hit_counts:
        avg_hits = sum(out_of_scope_hit_counts) / len(out_of_scope_hit_counts)
        print(f"\nOut-of-scope queries evaluated: {len(out_of_scope_hit_counts)}")
        print(f"  Average results returned for queries with NO relevant source: {avg_hits:.1f}")
        if avg_hits > 0:
            print("  (results are still coming back — either the relevance gate is off, or")
            print("   RERANK_RELEVANCE_THRESHOLD needs to be raised based on the rerank_score")
            print("   numbers printed above)")
        else:
            print("  (the relevance gate is working — nothing passed the threshold)")
