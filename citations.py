"""
STEP 9: CITATIONS — format retrieved chunks for handing to an LLM, and
for showing a human a readable, checkable reference list.
"""


def format_citation(metadata):
    """
    A short, human-readable citation tag for one chunk — used inline in
    the prompt (kept compact so it doesn't eat token budget).
    """
    source = metadata.get("source_file", "unknown source")
    page = metadata.get("page_number", "?")
    return f"[{source}, p.{page}]"


def format_reference_entry(index, result):
    """
    A FULL, human-readable reference block for one retrieved chunk — this
    is what makes a chunk easy to actually go find and check. Includes:
      - the source file and page (so you know which PDF/page to open)
      - the exact chunk_id (so you can grep chunks_metadata.json or the
        Chroma collection for this precise chunk, byte-for-byte)
      - which chunk this was on that page, and how it was matched/scored
      - a text preview long enough to recognize the passage at a glance
    """
    meta = result.get("metadata", {})
    source = meta.get("source_file", "unknown source")
    page = meta.get("page_number", "?")
    chunk_id = result.get("chunk_id", meta.get("chunk_id", "unknown_id"))
    chunk_pos = meta.get("chunk_index_in_page", "?")
    matched_by = result.get("matched_by", "n/a")
    rerank_score = result.get("rerank_score")
    fused_score = result.get("fused_score")

    score_bits = []
    if fused_score is not None:
        score_bits.append(f"fused={fused_score:.4f}")
    if rerank_score is not None:
        score_bits.append(f"rerank={rerank_score:.3f}")
    score_str = ", ".join(score_bits) if score_bits else "n/a"

    text = result.get("text", "")
    preview = text[:300].replace("\n", " ").strip()

    return (
        f"[{index}] {source} — page {page} (chunk #{chunk_pos} on that page)\n"
        f"    chunk_id: {chunk_id}\n"
        f"    matched_by: {matched_by} | scores: {score_str}\n"
        f"    preview: \"{preview}{'...' if len(text) > 300 else ''}\""
    )


def build_context_with_citations(results):
    """
    Format hybrid_search() results into numbered, cited blocks ready to
    paste straight into an LLM prompt — each block traceable back to its
    exact source file and page. Uses the compact format_citation() since
    this text goes into the LLM's context window, not to a human.
    """
    blocks = []
    for i, result in enumerate(results, start=1):
        citation = format_citation(result["metadata"])
        blocks.append(f"[{i}] {citation}\n{result['text']}")
    return "\n\n".join(blocks)


def print_readable_references(results):
    """
    Print a full, human-readable reference list — one detailed block per
    chunk — meant to sit right under an LLM's generated answer so you can
    immediately check any [n] citation it used against the exact chunk
    that produced it.
    """
    print("\nReferences:")
    for i, result in enumerate(results, start=1):
        print(format_reference_entry(i, result))


def get_readable_references(results):
    """Same content as print_readable_references(), returned as a string
    instead of printed — useful when calling from code that wants the
    text (e.g. a UI, a saved log) rather than stdout."""
    return "\n".join(format_reference_entry(i, r) for i, r in enumerate(results, start=1))
