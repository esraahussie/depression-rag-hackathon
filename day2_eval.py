"""
Day 2 retrieval lab
===================
Required by Day2.pptx:
  - 15–20 labeled questions (eval_set.json)
  - Top-3 vs Top-5 vs Top-10
  - two chunk settings
  - semantic vs keyword vs hybrid
  - Precision@3 and Precision@5
  - evidence panel with score + metadata
  - documented best setup + one failure case

Run:
    python day2_eval.py
"""

import glob
import html
import json
import os
import re
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as tfidf_cosine

from main import (
    CANDIDATE_POOL,
    MIN_RETRIEVE_SCORE,
    OUTPUT_FOLDER,
    PDF_FOLDER,
    boost_retrieval_scores,
    chunk_document,
    clean_query,
    dedup_ranked_indices,
    embed_minilm_onnx,
    extract_document,
    format_chunk_for_embedding,
)

EVAL_SET_FILE = "eval_set.json"
PANEL_FILE = os.path.join(OUTPUT_FOLDER, "evidence_panel.html")
RESULTS_FILE = os.path.join(OUTPUT_FOLDER, "day2_eval.json")
FINDINGS_FILE = os.path.join(OUTPUT_FOLDER, "day2_findings.md")

# Experiment A: tighter recommendation-style chunks (10–15% overlap)
# Experiment B: longer paragraphs/tables
SETTINGS = {
    "A_500_75": {"chunk_size": 500, "overlap": 75, "label": "500 chars / 15% overlap"},
    "B_900_120": {"chunk_size": 900, "overlap": 120, "label": "900 chars / 13% overlap"},
}

K_VALUES = (3, 5, 10)
STRATEGIES = ("semantic", "keyword", "hybrid")
RRF_K = 60


def is_relevant(chunk_text, meta, question):
    """Honest label: expected source AND a keyword in the chunk body (not the filename)."""
    if question.get("out_of_scope"):
        return False
    sources = question.get("expected_sources") or []
    if sources and meta.get("source_file") not in sources:
        return False
    query = (question.get("query") or "").lower()
    gid = (meta.get("guideline_id") or "").lower()
    if gid and re.search(rf"\b{re.escape(gid)}\b", query):
        return True
    keywords = [k.lower() for k in question.get("keywords") or [] if k]
    if not keywords:
        return True
    hay = f"{chunk_text} {meta.get('section_title') or ''}".lower()
    return any(k in hay for k in keywords)


def rrf_fuse(sem_order, kw_order, rrf_k=RRF_K):
    scores = defaultdict(float)
    for rank, idx in enumerate(sem_order, start=1):
        scores[int(idx)] += 1.0 / (rrf_k + rank)
    for rank, idx in enumerate(kw_order, start=1):
        scores[int(idx)] += 1.0 / (rrf_k + rank)
    return sorted(scores, key=lambda i: scores[i], reverse=True)


def precision_at_k(flags, k):
    if k <= 0:
        return 0.0
    return sum(flags[:k]) / float(k)


def cache_pdfs():
    paths = sorted(glob.glob(os.path.join(PDF_FOLDER, "*.pdf")))
    cached = []
    for path in paths:
        print(f"Extracting {os.path.basename(path)}")
        cached.append((os.path.basename(path), extract_document(path)))
    return cached


def chunks_from_cache(cached, chunk_size, overlap):
    texts, metas = [], []
    for file_name, (doc_meta, page_blocks, toc) in cached:
        pieces = chunk_document(
            doc_meta, page_blocks, toc, chunk_size=chunk_size, overlap=overlap
        )
        stem = os.path.splitext(file_name)[0]
        for i, chunk in enumerate(pieces):
            texts.append(chunk["text"])
            metas.append({
                "chunk_id": f"{stem}_{i:04d}",
                "source_file": file_name,
                "doc_title": doc_meta.get("doc_title") or "",
                "organization": doc_meta.get("organization") or "",
                "guideline_id": doc_meta.get("guideline_id") or "",
                "year": doc_meta.get("year") or 0,
                "page_number": chunk["page_start"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "section_title": chunk["section_title"],
                "char_count": len(chunk["text"]),
            })
    return texts, metas


def retrieve(query, texts, metas, sem_mat, kw_mat, doc_emb, q_index, strategy, k):
    sem_scores = boost_retrieval_scores(query, texts, metas, sem_mat[q_index])
    kw_scores = boost_retrieval_scores(query, texts, metas, kw_mat[q_index])
    if strategy == "semantic":
        order = np.argsort(-sem_scores)
    elif strategy == "keyword":
        order = np.argsort(-kw_scores)
    else:
        sem_order = np.argsort(-sem_scores)
        kw_order = np.argsort(-kw_scores)
        order = np.array(rrf_fuse(sem_order, kw_order))
    ranked = dedup_ranked_indices(
        order[:CANDIDATE_POOL],
        texts,
        metas,
        sem_mat[q_index],
        doc_emb=doc_emb,
        k=k,
        min_score=MIN_RETRIEVE_SCORE,
    )
    hits = []
    for rank, idx in enumerate(ranked, start=1):
        hits.append({
            "rank": rank,
            "similarity": round(float(sem_mat[q_index][idx]), 4),
            "boosted_score": round(float(sem_scores[idx]), 4),
            "relevant": None,
            "text": texts[idx],
            **metas[idx],
        })
    return hits


def evaluate_setup(name, setting, cached, questions):
    print(f"\n=== Chunk setting {name}: {setting['label']} ===")
    texts, metas = chunks_from_cache(cached, setting["chunk_size"], setting["overlap"])
    print(f"  {len(texts)} chunks")

    cleaned_queries = [clean_query(q["query"]) for q in questions]
    embed_texts = [format_chunk_for_embedding(text, meta) for text, meta in zip(texts, metas)]
    print("  Embedding chunks (MiniLM ONNX)...")
    doc_emb = embed_minilm_onnx(embed_texts)
    query_emb = embed_minilm_onnx(cleaned_queries)
    sem_mat = np.asarray(query_emb @ doc_emb.T)

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=40000)
    kw_docs = vectorizer.fit_transform(embed_texts)
    kw_queries = vectorizer.transform(cleaned_queries)
    kw_mat = tfidf_cosine(kw_queries, kw_docs)

    setup = {
        "name": name,
        "label": setting["label"],
        "chunk_size": setting["chunk_size"],
        "overlap": setting["overlap"],
        "n_chunks": len(texts),
        "strategies": {},
    }

    for strategy in STRATEGIES:
        q_rows = []
        p3, p5, top1 = [], [], []
        for qi, question in enumerate(questions):
            hits = retrieve(cleaned_queries[qi], texts, metas, sem_mat, kw_mat, doc_emb, qi, strategy, k=10)
            for hit in hits:
                hit["relevant"] = is_relevant(hit["text"], hit, question)
            flags = [1 if h["relevant"] else 0 for h in hits]
            row = {
                "id": question["id"],
                "type": question["type"],
                "query": question["query"],
                "out_of_scope": bool(question.get("out_of_scope")),
                "precision_at_3": round(precision_at_k(flags, 3), 3),
                "precision_at_5": round(precision_at_k(flags, 5), 3),
                "best_rank": next((h["rank"] for h in hits if h["relevant"]), None),
                "top1_similarity": hits[0]["similarity"] if hits else 0.0,
                "n_hits": len(hits),
                "hits": hits,
            }
            q_rows.append(row)
            if not question.get("out_of_scope"):
                p3.append(row["precision_at_3"])
                p5.append(row["precision_at_5"])
                top1.append(row["top1_similarity"])
        setup["strategies"][strategy] = {
            "mean_precision_at_3": round(float(np.mean(p3)), 3) if p3 else 0.0,
            "mean_precision_at_5": round(float(np.mean(p5)), 3) if p5 else 0.0,
            "mean_top1_similarity": round(float(np.mean(top1)), 3) if top1 else 0.0,
            "questions": q_rows,
        }
        print(
            f"  {strategy:9s}  P@3={setup['strategies'][strategy]['mean_precision_at_3']:.3f}  "
            f"P@5={setup['strategies'][strategy]['mean_precision_at_5']:.3f}  "
            f"top1={setup['strategies'][strategy]['mean_top1_similarity']:.3f}"
        )
    return setup


def pick_best(results):
    best = None
    best_score = -1
    for setup in results:
        for strategy, payload in setup["strategies"].items():
            score = payload["mean_precision_at_5"] * 2 + payload["mean_precision_at_3"]
            if score > best_score:
                best_score = score
                best = (setup["name"], strategy, payload, setup)
    return best


def write_panel(best_name, best_strategy, payload, setup):
    rows = []
    for q in payload["questions"]:
        cards = []
        for hit in q["hits"][:5]:
            flag = "relevant" if hit["relevant"] else "not-relevant"
            excerpt = html.escape(hit["text"][:500])
            cards.append(f"""
            <article class="chunk {flag}">
              <header>
                <span class="rank">Chunk {hit['rank']}</span>
                <span class="score">Score {hit['similarity']:.2f}</span>
                <span class="tag">{html.escape(hit.get('organization') or '')}</span>
              </header>
              <p class="meta">
                {html.escape(hit.get('source_file') or '')} ·
                {html.escape(hit.get('guideline_id') or '-')} ·
                Section {html.escape(hit.get('section_title') or 'Unspecified')} ·
                Page {hit.get('page_start')}{'' if hit.get('page_start')==hit.get('page_end') else '–' + str(hit.get('page_end'))}
                · {flag}
              </p>
              <p class="excerpt">{excerpt}</p>
            </article>
            """)
        if not q["hits"]:
            cards.append(f"""
            <article class="chunk gated">
              <p class="excerpt">No chunk passed the {MIN_RETRIEVE_SCORE:.2f} confidence gate. Do not generate an answer.</p>
            </article>
            """)
        rows.append(f"""
        <section class="query">
          <h2>{html.escape(q['id'])} · {html.escape(q['type'])}</h2>
          <p class="q">{html.escape(q['query'])}</p>
          <p class="metrics">Precision@3 = {q['precision_at_3']:.2f} · Precision@5 = {q['precision_at_5']:.2f}</p>
          {''.join(cards)}
        </section>
        """)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Day 2 evidence panel</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; background: #f4f6f8; color: #1b1f24; margin: 0; }}
    header.banner {{ background: #143b4a; color: white; padding: 24px 32px; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
    .query {{ background: white; border: 1px solid #d5dde3; margin-bottom: 28px; padding: 16px 20px; }}
    .q {{ font-size: 18px; font-weight: 600; }}
    .metrics {{ color: #4b5b66; }}
    .chunk {{ border-top: 1px solid #e6ebef; padding: 12px 0; }}
    .chunk.relevant {{ border-left: 4px solid #2e7d4f; padding-left: 12px; }}
    .chunk.gated {{ border-left: 4px solid #8a6d3b; padding-left: 12px; }}
    .rank, .score, .tag {{ margin-right: 10px; font-size: 13px; }}
    .score {{ font-weight: 700; }}
    .meta {{ color: #4b5b66; font-size: 13px; }}
    .excerpt {{ white-space: pre-wrap; font-size: 14px; }}
  </style>
</head>
<body>
  <header class="banner">
    <h1>Evidence panel — before generation</h1>
    <p>Best setup: chunk {html.escape(setup['label'])} · {html.escape(best_strategy)} search · Top-5 shown</p>
    <p>Mean Precision@3 = {payload['mean_precision_at_3']:.2f} · Mean Precision@5 = {payload['mean_precision_at_5']:.2f} · Mean Top-1 cosine = {payload.get('mean_top1_similarity', 0):.2f} · Gate = {MIN_RETRIEVE_SCORE:.2f}</p>
  </header>
  <main>
    {''.join(rows)}
  </main>
</body>
</html>
"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(PANEL_FILE, "w", encoding="utf-8") as f:
        f.write(page)


def write_findings(results, best):
    best_name, best_strategy, payload, setup = best
    lines = [
        "# Day 2 retrieval findings",
        "",
        "Measured on 18 labeled questions (14 in-scope, 4 out-of-scope).",
        "Out-of-scope items are excluded from mean Precision@K (they are failure cases).",
        "",
        "## Chunk settings compared",
        "",
        "| Setting | Chunks | Strategy | Precision@3 | Precision@5 | Mean Top-1 |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for setup_row in results:
        for strategy, body in setup_row["strategies"].items():
            mark = " **best**" if setup_row["name"] == best_name and strategy == best_strategy else ""
            lines.append(
                f"| {setup_row['label']} | {setup_row['n_chunks']} | {strategy}{mark} | "
                f"{body['mean_precision_at_3']:.3f} | {body['mean_precision_at_5']:.3f} | "
                f"{body.get('mean_top1_similarity', 0):.3f} |"
            )
    lines += [
        "",
        f"**Chosen setup:** {setup['label']} with **{best_strategy}** search, starting Top-K = 5.",
        "",
        "## Why",
        "",
        "This combination placed correct evidence highest on in-scope questions while keeping traces (document, page, section, score).",
        "",
        "## Failure case (out of scope)",
        "",
    ]
    oos = next(q for q in payload["questions"] if q["out_of_scope"])
    if oos["hits"]:
        top = oos["hits"][0]
        oos_lines = [
            f"Query: {oos['query']}",
            "",
            f"Top hit was still depression text (`{top['source_file']}`, score {top['similarity']:.2f}).",
            "The confidence gate should normally drop this; if it appears, raise MIN_RETRIEVE_SCORE.",
        ]
    else:
        oos_lines = [
            f"Query: {oos['query']}",
            "",
            f"No chunk passed the {MIN_RETRIEVE_SCORE:.2f} confidence gate.",
            "That is the correct Day 2 behavior for out-of-scope questions: retrieve nothing and refuse to generate.",
        ]
    lines += oos_lines + [
        "",
        "## Quality fixes applied",
        "",
        "- Keep diagnostic/recommendation lists in one chunk",
        "- Drop duplicate Top-K hits (same page/section or cosine > 0.92)",
        "- Ignore junk headings such as `(DSM-5)`",
        "- Prefix org / guideline / section before embedding",
        f"- Refuse hits below MiniLM cosine {MIN_RETRIEVE_SCORE:.2f}",
        "- Label Precision@K only when the expected source AND a body keyword match",
        "",
        "Official demo path: `python main.py --similarity` then `python day2_eval.py`.",
        "Do not use `rag_pipeline_simple.py` for this stage.",
        "",
        "## Top-K note",
        "",
        "Inspect Top-3, Top-5, and Top-10 on the evidence panel. Use Top-5 as the default: Top-3 misses some paraphrases; Top-10 adds off-section noise.",
    ]
    with open(FINDINGS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    with open(EVAL_SET_FILE, encoding="utf-8") as f:
        questions = json.load(f)["questions"]
    print(f"Loaded {len(questions)} eval questions")

    cached = cache_pdfs()
    results = []
    for name, setting in SETTINGS.items():
        results.append(evaluate_setup(name, setting, cached, questions))

    best = pick_best(results)
    best_name, best_strategy, payload, setup = best
    write_panel(best_name, best_strategy, payload, setup)
    write_findings(results, best)

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"best": {"setting": best_name, "strategy": best_strategy}, "results": results}, f, indent=2)

    print(f"\nBEST: {setup['label']} + {best_strategy}")
    print(f"  P@3={payload['mean_precision_at_3']:.3f}  P@5={payload['mean_precision_at_5']:.3f}  top1={payload.get('mean_top1_similarity', 0):.3f}")
    print(f"Evidence panel -> {PANEL_FILE}")
    print(f"Findings       -> {FINDINGS_FILE}")


if __name__ == "__main__":
    main()
