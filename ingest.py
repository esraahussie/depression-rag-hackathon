"""
STEP 4: RUN THE PIPELINE (extract -> clean -> chunk -> save metadata)
STEP 5: EMBED CHUNKS INTO CHROMA + build the BM25 keyword index

This is the expensive, one-time part of the pipeline. Everything it
produces gets cached to disk (outputs/corpus_cache.pkl, outputs/bm25_index.pkl,
outputs/chroma_db/) so pipeline.load_or_build_index() can skip straight to
loading on every run after the first — see pipeline.py.
"""

import glob
import json
import os
import pickle

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

from settings import (
    PDF_FOLDER, OUTPUT_FOLDER, METADATA_FILE, CORPUS_CACHE_FILE, BM25_CACHE_FILE,
    CHROMA_FOLDER, COLLECTION_NAME, EMBEDDING_MODEL, MIN_CHUNK_WORDS,
    USE_SEMANTIC_CHUNKING,
)
from extraction import extract_text_from_pdf
from cleaning import clean_text
from chunking import chunk_text, semantic_chunk_text


# ---------------------------------------------------------------------
# STEP 4: chunks + metadata
# ---------------------------------------------------------------------

def build_chunks_and_metadata():
    """
    Reads every PDF in PDF_FOLDER, cleans + chunks the text, and returns
    (chunk_texts, chunk_ids, metadata_list). Also writes chunks_metadata.json
    for human inspection.
    """
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_paths = sorted(glob.glob(os.path.join(PDF_FOLDER, "*.pdf")))
    if not pdf_paths:
        print(f"No PDFs found in '{PDF_FOLDER}/'. Add some and rerun.")
        return [], [], []

    all_chunk_texts = []
    all_chunk_ids = []
    all_metadata = []

    for pdf_path in pdf_paths:
        file_name = os.path.basename(pdf_path)
        base_name = os.path.splitext(file_name)[0]
        print(f"\nProcessing: {file_name}")

        pages = extract_text_from_pdf(pdf_path)
        doc_chunk_count = 0

        for page_number, raw_page_text in pages:
            cleaned = clean_text(raw_page_text)
            if not cleaned:
                continue

            page_chunks = semantic_chunk_text(cleaned) if USE_SEMANTIC_CHUNKING else chunk_text(cleaned)
            page_chunks = [c for c in page_chunks if len(c.split()) >= MIN_CHUNK_WORDS]

            if not page_chunks:
                continue

            for chunk_index_in_page, chunk in enumerate(page_chunks, start=1):
                chunk_id = f"{base_name}_p{page_number:03d}_c{chunk_index_in_page:02d}"
                doc_chunk_count += 1

                all_chunk_texts.append(chunk)
                all_chunk_ids.append(chunk_id)
                all_metadata.append({
                    "chunk_id": chunk_id,
                    "source_file": file_name,
                    "page_number": page_number,
                    "chunk_index_in_page": chunk_index_in_page,
                    "chunk_index_in_doc": doc_chunk_count,
                    "char_count": len(chunk),
                    "text_preview": chunk[:200],
                })

            print(f"  Page {page_number}: {len(page_chunks)} chunk(s)")

        print(f"  Total for {file_name}: {doc_chunk_count} chunks")

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
    print(f"\nSaved metadata for {len(all_metadata)} chunks -> {METADATA_FILE}")

    return all_chunk_texts, all_chunk_ids, all_metadata


# ---------------------------------------------------------------------
# STEP 5: embeddings (Chroma) + keyword index (BM25)
# ---------------------------------------------------------------------

def embed_chunks(chunk_texts, chunk_ids, metadata_list):
    """
    Embeds chunks into a persistent Chroma collection. Idempotent: if the
    collection already has these chunks (e.g. loaded from disk on a
    previous run), it skips re-adding them instead of duplicating.
    """
    print("\nLoading embedding model (first run downloads it, needs internet)...")

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    # NOTE: named chroma_client (not `client`) so it never collides with
    # the LLM `client` imported from config.py elsewhere in the project.
    chroma_client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    if collection.count() >= len(chunk_texts):
        print(f"Collection already has {collection.count()} chunks — skipping re-embedding.")
        return collection

    simple_metadata = [
        {
            "source_file": m["source_file"],
            "page_number": m["page_number"],
            "chunk_index_in_page": m["chunk_index_in_page"],
            "chunk_index_in_doc": m["chunk_index_in_doc"],
        }
        for m in metadata_list
    ]

    batch_size = 64
    for i in range(0, len(chunk_texts), batch_size):
        collection.add(
            documents=chunk_texts[i:i + batch_size],
            ids=chunk_ids[i:i + batch_size],
            metadatas=simple_metadata[i:i + batch_size],
        )

    print(f"Embedded {collection.count()} chunks -> {CHROMA_FOLDER}")
    return collection


def get_chroma_collection():
    """Open the existing persistent Chroma collection without re-embedding anything."""
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    chroma_client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )


def build_bm25_index(chunk_texts):
    """Build a keyword-search index over all chunks (run once after ingestion)."""
    from retrieval import simple_tokenize  # local import avoids a circular import at module load time
    tokenized_corpus = [simple_tokenize(t) for t in chunk_texts]
    return BM25Okapi(tokenized_corpus)


# ---------------------------------------------------------------------
# Disk caching — so build_chunks_and_metadata() / build_bm25_index() only
# ever run once per corpus, not on every program run
# ---------------------------------------------------------------------

def corpus_cache_exists():
    return os.path.exists(CORPUS_CACHE_FILE) and os.path.exists(BM25_CACHE_FILE)


def save_corpus_cache(chunk_texts, chunk_ids, metadata_list):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(CORPUS_CACHE_FILE, "wb") as f:
        pickle.dump(
            {"chunk_texts": chunk_texts, "chunk_ids": chunk_ids, "metadata_list": metadata_list},
            f,
        )


def load_corpus_cache():
    with open(CORPUS_CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    return data["chunk_texts"], data["chunk_ids"], data["metadata_list"]


def save_bm25_cache(bm25_index):
    with open(BM25_CACHE_FILE, "wb") as f:
        pickle.dump(bm25_index, f)


def load_bm25_cache():
    with open(BM25_CACHE_FILE, "rb") as f:
        return pickle.load(f)
