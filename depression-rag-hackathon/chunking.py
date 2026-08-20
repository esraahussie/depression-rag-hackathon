"""
STEP 3: CHUNK TEXT (recursive character splitting)
STEP 3b: CONTEXT-AWARE (SEMANTIC) CHUNKING — an alternative to chunk_text()
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer

from settings import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, SEMANTIC_SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------
# Fixed-size recursive splitting (default)
# ---------------------------------------------------------------------

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP, separators=None):
    """
    Recursive character splitting: try to split on natural boundaries first
    (paragraphs, then lines, then sentences, then words), falling back to
    raw characters only as a last resort. Keeps chunks close to whole
    sentences/paragraphs instead of cutting mid-word or mid-sentence.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    return _split_text(text, separators, chunk_size, overlap)


def _split_text(text, separators, chunk_size, overlap):
    separator = separators[-1]
    remaining_separators = []
    for i, sep in enumerate(separators):
        if sep == "" or sep in text:
            separator = sep
            remaining_separators = separators[i + 1:]
            break

    pieces = text.split(separator) if separator else list(text)

    good_pieces = []
    for piece in pieces:
        if len(piece) <= chunk_size or not remaining_separators:
            good_pieces.append(piece)
        else:
            good_pieces.extend(_split_text(piece, remaining_separators, chunk_size, overlap))

    return _merge_pieces(good_pieces, separator, chunk_size, overlap)


def _merge_pieces(pieces, separator, chunk_size, overlap):
    """Greedily glue small pieces back together into chunks close to chunk_size,
    carrying a bit of overlap into the next chunk so context isn't lost."""
    chunks = []
    current = []
    current_len = 0

    for piece in pieces:
        piece_len = len(piece) + len(separator)

        if current and current_len + piece_len > chunk_size:
            chunk = separator.join(current).strip()
            if chunk:
                chunks.append(chunk)

            overlap_pieces = []
            overlap_len = 0
            for p in reversed(current):
                overlap_len += len(p) + len(separator)
                if overlap_len > overlap:
                    break
                overlap_pieces.insert(0, p)
            current = overlap_pieces
            current_len = sum(len(p) + len(separator) for p in current)

        current.append(piece)
        current_len += piece_len

    if current:
        chunk = separator.join(current).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


# ---------------------------------------------------------------------
# Semantic (embedding-based) splitting — optional alternative
# ---------------------------------------------------------------------

_semantic_model = None  # loaded once and reused, so we don't reload it per PDF


def get_embedding_model(model_name=EMBEDDING_MODEL):
    global _semantic_model
    if _semantic_model is None:
        _semantic_model = SentenceTransformer(model_name)
    return _semantic_model


def split_into_sentences(text):
    """Basic sentence splitter — good enough for chunking purposes."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def cosine_similarity(vec_a, vec_b):
    return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))


def semantic_chunk_text(text, chunk_size=CHUNK_SIZE, similarity_threshold=SEMANTIC_SIMILARITY_THRESHOLD):
    """
    Context-aware chunking: group sentences together while they stay on the
    same topic, and start a new chunk when the topic shifts or the current
    chunk gets too big.
    """
    sentences = split_into_sentences(text)
    if len(sentences) <= 1:
        return [text] if text.strip() else []

    model = get_embedding_model()
    embeddings = model.encode(sentences)

    chunks = []
    current_sentences = [sentences[0]]
    current_length = len(sentences[0])

    for i in range(1, len(sentences)):
        similarity = cosine_similarity(embeddings[i - 1], embeddings[i])
        next_length = current_length + len(sentences[i])

        topic_changed = similarity < similarity_threshold
        too_big = next_length > chunk_size

        if (topic_changed or too_big) and current_sentences:
            chunks.append(" ".join(current_sentences))
            current_sentences = [sentences[i]]
            current_length = len(sentences[i])
        else:
            current_sentences.append(sentences[i])
            current_length = next_length

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks
