"""
Citations — assign stable IDs, build LLM context, validate markers, format API sources.
"""

import re

from relevance import get_relevance_score
from confidence import normalize_score

SOURCE_DISPLAY_NAMES = {
    "WHOEMMNH219E-eng.pdf": "WHO Clinical Depression Guide",
    "depression-treatment-and-management.pdf": "Treatment Guidelines",
    "depression-in-adults-with-a-chronic-physical-health-problem.pdf": "Depression & Chronic Health",
    "depression-in-children-and-young-people.pdf": "Depression in Young People",
    "depression-suicide-risk-adults.pdf": "Suicide Risk Assessment",
    "nice-depression-guideline.pdf": "NICE Depression Guideline",
    "phq9-reference.pdf": "PHQ-9 Reference",
}


def prettify_source_name(source_file: str) -> str:
    if source_file in SOURCE_DISPLAY_NAMES:
        return SOURCE_DISPLAY_NAMES[source_file]

    lower = source_file.lower()
    keyword_names = [
        (("phq", "phq-9"), "PHQ-9 Reference"),
        (("treatment-and-management", "treatment and management"), "Treatment Guidelines"),
        (("suicide-risk", "suicide risk"), "Suicide Risk Assessment"),
        (("children-and-young", "children and young"), "Depression in Young People"),
        (("chronic-physical", "chronic physical"), "Depression & Chronic Health"),
        (("whoemmnh219",), "WHO Clinical Depression Guide"),
        (("whoemmnh222",), "WHO Depression Factsheet"),
        (("screening", "final-recommendation"), "Clinical Screening Guidelines"),
        (("anxiety-adults",), "Adult Anxiety Screening"),
    ]
    for keys, label in keyword_names:
        if any(k in lower for k in keys):
            return label

    name = source_file.replace(".pdf", "")
    name = re.sub(r"[-_]+", " ", name)
    name = re.sub(r"\s+\d{5,}\s*$", "", name)
    return name.strip().title() or "Clinical Reference"


def assign_citation_ids(results: list[dict]) -> list[dict]:
    """Attach sequential citation_id (1..n) to each retrieved chunk."""
    annotated = []
    for i, result in enumerate(results, start=1):
        entry = dict(result)
        entry["citation_id"] = i
        annotated.append(entry)
    return annotated


def get_chunk_number(metadata: dict, chunk_id: str | None = None) -> int | None:
    """
    Stable chunk identifier for display. Prefer chunk_index_in_doc, then
    chunk_index_in_page. Never invent a value.
    """
    if metadata.get("chunk_index_in_doc") is not None:
        return int(metadata["chunk_index_in_doc"])
    if metadata.get("chunk_index_in_page") is not None:
        return int(metadata["chunk_index_in_page"])
    return None


def get_page_number(metadata: dict) -> int | None:
    page = metadata.get("page_number")
    return int(page) if page is not None else None


def result_to_source(result: dict) -> dict:
    """Build one API source object from a cited retrieval result."""
    meta = result.get("metadata", {})
    source_file = meta.get("source_file", "unknown source")
    raw_score = get_relevance_score(result)
    norm_score = round(normalize_score(raw_score), 2) if raw_score is not None else None

    return {
        "citation_id": result["citation_id"],
        "pdf": source_file,
        "name": prettify_source_name(source_file),
        "page": get_page_number(meta),
        "chunk": get_chunk_number(meta, result.get("chunk_id")),
        "relevance_score": norm_score,
    }


def build_context_with_citations(results: list[dict]) -> str:
    """Numbered context blocks for the LLM — citation_id matches [n] markers."""
    blocks = []
    for result in results:
        cid = result["citation_id"]
        meta = result["metadata"]
        source = meta.get("source_file", "unknown source")
        page = meta.get("page_number")
        page_str = f"p.{page}" if page is not None else "p.?"
        blocks.append(f"[{cid}] [{source}, {page_str}]\n{result['text']}")
    return "\n\n".join(blocks)


def build_source_legend(results: list[dict]) -> str:
    """Human-readable legend the LLM must respect when citing."""
    lines = []
    for result in results:
        src = result_to_source(result)
        page = src["page"] if src["page"] is not None else "N/A"
        chunk = src["chunk"] if src["chunk"] is not None else "N/A"
        lines.append(
            f"[{src['citation_id']}] {src['name']} | PDF: {src['pdf']} | "
            f"Page: {page} | Chunk: {chunk}"
        )
    return "\n".join(lines)


_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def extract_citation_ids(text: str) -> set[int]:
    return {int(m) for m in _CITATION_PATTERN.findall(text)}


def validate_and_clean_citations(answer: str, valid_ids: set[int]) -> tuple[str, set[int]]:
    """
    Remove invalid [n] markers (e.g. [7] when only [1]-[3] exist).
    Returns cleaned answer and the set of valid IDs actually used.
    """
    if not valid_ids:
        cleaned = _CITATION_PATTERN.sub("", answer)
        return re.sub(r"  +", " ", cleaned).strip(), set()

    used: set[int] = set()

    def _replace(match: re.Match) -> str:
        cid = int(match.group(1))
        if cid in valid_ids:
            used.add(cid)
            return match.group(0)
        return ""

    cleaned = _CITATION_PATTERN.sub(_replace, answer)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\s+([.!?,])", r"\1", cleaned)
    return cleaned.strip(), used


def filter_cited_sources(results: list[dict], used_ids: set[int]) -> list[dict]:
    """Keep only sources whose citation_id appears in the answer."""
    return [r for r in results if r["citation_id"] in used_ids]


def uncited_results(results: list[dict], used_ids: set[int]) -> list[dict]:
    return [r for r in results if r["citation_id"] not in used_ids]


# ------------------------------------------------------------------
# CLI / debug helpers (used by main.py)
# ------------------------------------------------------------------

def format_citation(metadata):
    source = metadata.get("source_file", "unknown source")
    page = metadata.get("page_number", "?")
    return f"[{source}, p.{page}]"


def format_reference_entry(index, result):
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


def print_readable_references(results):
    print("\nReferences:")
    for i, result in enumerate(results, start=1):
        print(format_reference_entry(i, result))


def get_readable_references(results):
    return "\n".join(format_reference_entry(i, r) for i, r in enumerate(results, start=1))
