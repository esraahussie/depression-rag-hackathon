"""Quick validation of MindCare RAG improvements (Tests 1-6)."""

import sys

from citations import assign_citation_ids, validate_and_clean_citations, result_to_source
from pipeline import load_or_build_index, ask


def safe_print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


def test_citation_validation():
    results = assign_citation_ids([{"metadata": {}, "text": "a", "fused_score": 0.1} for _ in range(3)])
    valid = {r["citation_id"] for r in results}
    cleaned, used = validate_and_clean_citations("Common in depression [7] and anxiety [2].", valid)
    assert "[7]" not in cleaned
    assert "[2]" in cleaned
    assert used == {2}
    print("Test 5 PASS — invalid [7] removed, [2] kept")


def test_missing_metadata():
    result = assign_citation_ids([{
        "metadata": {"source_file": "test.pdf"},
        "text": "sample",
        "fused_score": 0.5,
        "citation_id": 1,
    }])[0]
    src = result_to_source(result)
    assert src["page"] is None
    assert src["chunk"] is None
    print("Test 6 PASS — missing page/chunk return null")


def main():
    test_citation_validation()
    test_missing_metadata()

    print("\nLoading index...")
    index = load_or_build_index()

    cases = [
        ("Test 1 — Relevant", "What are common symptoms of depression?"),
        ("Test 2 — Irrelevant", "What is the capital of France?"),
        ("Test 3 — MH but unsupported", "What is the recommended dosage of lithium for bipolar disorder in elderly patients?"),
        ("Test 4 — Multiple citations", "What treatment options exist for depression including therapy and medication?"),
    ]

    for label, query in cases:
        print("\n" + "=" * 70)
        print(label)
        print(f"Q: {query}")
        r = ask(index, query, n_results=5)
        safe_print(f"Status: {r['status']}  Confidence: {r['confidence']}")
        ans = r['answer'][:300] + ('...' if len(r['answer']) > 300 else '')
        safe_print(f"Answer: {ans}")
        safe_print(f"Sources ({len(r['sources'])}):")
        for s in r["sources"]:
            safe_print(f"  [{s['citation_id']}] {s['name']} | pdf={s['pdf']} page={s['page']} chunk={s['chunk']} rel={s['relevance_score']}")
        if r.get("additional_sources"):
            safe_print(f"Additional ({len(r['additional_sources'])})")


if __name__ == "__main__":
    main()
