"""
Entry point.

Usage:
    python main.py "your question here"     -> answers one query and exits
    python main.py                          -> interactive loop, ask multiple questions
    python main.py --rebuild                -> force re-ingestion of pdfs/ even if a cache exists
    python main.py --eval                   -> run the precision/recall evaluation suite on TEST_QUERIES

Ingestion (PDF extraction, chunking, embedding, BM25 indexing) only runs
once — after that, load_or_build_index() loads everything from disk in
seconds. See pipeline.py for that logic.
"""

import argparse

from pipeline import load_or_build_index, ask
from citations import print_readable_references
from evaluation import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="Depression Clinical RAG")
    parser.add_argument("query", nargs="?", default=None,
                         help="Question to ask. If omitted, starts an interactive loop.")
    parser.add_argument("--rebuild", action="store_true",
                         help="Force re-ingestion of pdfs/ even if a cache already exists.")
    parser.add_argument("--eval", action="store_true",
                         help="Run the precision/recall evaluation suite on TEST_QUERIES instead of answering a query.")
    parser.add_argument("--n-results", type=int, default=5,
                         help="Number of chunks to retrieve/cite per query (default: 5).")
    parser.add_argument("--no-gate", action="store_true",
                         help="Disable the relevance gate (return results even below RERANK_RELEVANCE_THRESHOLD).")
    parser.add_argument("--language", default="auto",
                         choices=["auto", "en", "arz"],
                         help="Response language: auto (detect), en, or arz (Egyptian Arabic).")
    args = parser.parse_args()

    index = load_or_build_index(force_rebuild=args.rebuild)

    if args.eval:
        collection, bm25_index, chunk_texts, chunk_ids, metadata_list = index
        run_evaluation(collection, bm25_index, chunk_texts, chunk_ids, metadata_list,
                        use_relevance_gate=not args.no_gate)
        return

    if args.query:
        result = ask(index, args.query, n_results=args.n_results,
                     language=args.language,
                     use_relevance_gate=not args.no_gate)
        print(f"\nAnswer:\n{result['answer']}")
        print(f"Confidence: {result['confidence']:.0%}  Status: {result['status']}")
        if result["sources"]:
            print("\nSupporting sources:")
            for s in result["sources"]:
                page = s["page"] if s["page"] is not None else "N/A"
                chunk = s["chunk"] if s["chunk"] is not None else "N/A"
                rel = f"{s['relevance_score']:.2f}" if s["relevance_score"] is not None else "N/A"
                print(f"  [{s['citation_id']}] {s['name']} | PDF: {s['pdf']} | Page: {page} | Chunk: {chunk} | Relevance: {rel}")
                if s.get("source_url"):
                    print(f"      {s['source_url']}")
        print_readable_references(result["results"])
        return

    # interactive loop — index stays loaded in memory between questions
    print("\nReady. Type a question (or 'quit' to exit).")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query or query.lower() in ("quit", "exit"):
            break

        result = ask(index, query, n_results=args.n_results,
                       language=args.language,
                       use_relevance_gate=not args.no_gate)
        print(f"\nAnswer:\n{result['answer']}")
        print(f"Confidence: {result['confidence']:.0%}  Status: {result['status']}")
        if result["sources"]:
            print("\nSupporting sources:")
            for s in result["sources"]:
                page = s["page"] if s["page"] is not None else "N/A"
                chunk = s["chunk"] if s["chunk"] is not None else "N/A"
                rel = f"{s['relevance_score']:.2f}" if s["relevance_score"] is not None else "N/A"
                print(f"  [{s['citation_id']}] {s['name']} | PDF: {s['pdf']} | Page: {page} | Chunk: {chunk} | Relevance: {rel}")
                if s.get("source_url"):
                    print(f"      {s['source_url']}")
        print_readable_references(result["results"])


if __name__ == "__main__":
    main()
