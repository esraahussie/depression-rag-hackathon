"""
Orchestration layer. This is what main.py calls.

load_or_build_index() is the piece that stops you from re-running PDF
extraction / chunking / embedding on every program start: it checks for
cached files on disk first (outputs/corpus_cache.pkl, outputs/bm25_index.pkl,
outputs/chroma_db/) and only re-ingests when they're missing or --rebuild
is passed. Once loaded, the index is kept in memory for the life of the
process (see main.py's interactive loop) so repeated queries in one run
are instant too.

ask() is the single function that ties retrieval + generation + citations
together: give it a query, get back (answer, results) where `results` can
be handed to citations.print_readable_references() / get_readable_references().
"""

from ingest import (
    build_chunks_and_metadata, embed_chunks, build_bm25_index, get_chroma_collection,
    corpus_cache_exists, save_corpus_cache, load_corpus_cache,
    save_bm25_cache, load_bm25_cache,
)
from retrieval import hybrid_search
from generation import generate_answer


def load_or_build_index(force_rebuild=False):
    """
    Returns (collection, bm25_index, chunk_texts, chunk_ids, metadata_list).
    Loads from disk cache unless force_rebuild=True or the cache is missing,
    in which case it runs the full ingestion pipeline once and saves the
    result for next time.
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


def ask(index, query, n_results=5, **search_kwargs):
    """
    End-to-end: retrieve -> generate -> return (answer, results).
    `index` is the tuple returned by load_or_build_index().
    `results` (a list of hybrid_search result dicts) can be passed to
    citations.print_readable_references() or citations.get_readable_references().
    """
    collection, bm25_index, chunk_texts, chunk_ids, metadata_list = index

    results = hybrid_search(
        collection, bm25_index, chunk_texts, chunk_ids, metadata_list,
        query, n_results=n_results, verbose=False, **search_kwargs
    )

    answer = generate_answer(query, results)
    return answer, results
