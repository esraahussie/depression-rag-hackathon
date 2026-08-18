"""
All tunable settings and file paths for the RAG pipeline, in one place.
Nothing in here does any work — just constants — so every other module
can import from here without triggering side effects.
"""

import os

# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

PDF_FOLDER = "pdfs"                    # put all your PDFs in this folder
OUTPUT_FOLDER = "outputs"

METADATA_FILE = os.path.join(OUTPUT_FOLDER, "chunks_metadata.json")  # human-readable
CORPUS_CACHE_FILE = os.path.join(OUTPUT_FOLDER, "corpus_cache.pkl")   # chunk_texts + chunk_ids + metadata_list, for fast reload
BM25_CACHE_FILE = os.path.join(OUTPUT_FOLDER, "bm25_index.pkl")       # pickled BM25Okapi index
CHROMA_FOLDER = os.path.join(OUTPUT_FOLDER, "chroma_db")
COLLECTION_NAME = "depression_clinical"

# ---------------------------------------------------------------------
# CHUNKING
# ---------------------------------------------------------------------

CHUNK_SIZE = 1000          # characters per chunk (simple + common baseline approach)
CHUNK_OVERLAP = 150        # characters of overlap between chunks
MIN_CHUNK_WORDS = 12       # drop chunks shorter than this — usually titles/headers/boilerplate, not real content

USE_SEMANTIC_CHUNKING = False         # set True to use context-aware chunking instead
SEMANTIC_SIMILARITY_THRESHOLD = 0.5   # lower similarity than this = topic change = new chunk

# ---------------------------------------------------------------------
# EMBEDDING
# ---------------------------------------------------------------------

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------
# HYBRID SEARCH
# ---------------------------------------------------------------------

HYBRID_CANDIDATE_POOL = 50   # each search method retrieves this many candidates before filtering
RRF_K = 60                   # standard constant for reciprocal rank fusion (60 is the common default)

# ---------------------------------------------------------------------
# RERANKING
# ---------------------------------------------------------------------

USE_RERANKING = True
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_POOL = 10   # how many fused candidates get passed into the reranker

# The cross-encoder gives every candidate a "does this passage actually
# answer this query" score. Any result scoring BELOW this cutoff gets
# dropped instead of returned — this is the "no relevant information
# found" gate for genuinely out-of-scope queries. RECALIBRATE this once
# you can see real rerank_score numbers printed for your own relevant vs.
# out-of-scope queries.
RERANK_RELEVANCE_THRESHOLD = 2.0

# Below the main gate but above noise — "related topic, weak evidence".
INSUFFICIENT_EVIDENCE_THRESHOLD = 0.5

# Used when reranking is disabled (fused RRF scores are much smaller).
FUSED_RELEVANCE_THRESHOLD = 0.012

# ---------------------------------------------------------------------
# EVALUATION
# ---------------------------------------------------------------------

EVAL_K_VALUES = [1, 3, 5]    # which k values to report precision/recall at

# Each test query is paired with the source PDFs that would make a result
# genuinely relevant to it — "relevant_keywords" are substrings matched
# against source_file (case-insensitive). ADJUST THESE to match whatever
# PDFs are actually in your pdfs/ folder. An empty list means "this query
# is genuinely out of scope for this corpus".
TEST_QUERIES = [
    {"query": "What are the core diagnostic symptoms of major depressive disorder?",
     "relevant_keywords": ["treatment-and-management", "chronic-physical-health-problem", "children-and-young-people"]},
    {"query": "What treatment options are effective for depression, including medication and therapy?",
     "relevant_keywords": ["treatment-and-management"]},
    {"query": "How is depression severity measured or screened in clinical settings?",
     "relevant_keywords": ["treatment-and-management", "suicide-risk-adults"]},
]

# ---------------------------------------------------------------------
# GENERATION
# ---------------------------------------------------------------------

GENERATION_MODEL = "openai/gpt-oss-120b"

GENERATION_SYSTEM_PROMPT = (
    "You are a clinical evidence assistant for MindCare. Answer ONLY using the "
    "numbered source passages provided. Rules:\n"
    "1. Every factual claim MUST end with a [n] citation matching a provided source ID.\n"
    "2. ONLY use citation IDs listed in the Source Index — never invent new numbers.\n"
    "3. If the passages lack enough information, say so explicitly. Do not guess.\n"
    "4. Do not use outside knowledge. Do not answer off-topic questions."
)
