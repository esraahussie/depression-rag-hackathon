# Day 2 retrieval findings

Measured on 18 labeled questions (14 in-scope, 4 out-of-scope).
Out-of-scope items are excluded from mean Precision@K (they are failure cases).

## Chunk settings compared

| Setting | Chunks | Strategy | Precision@3 | Precision@5 | Mean Top-1 |
|---|---:|---|---:|---:|---:|
| 500 chars / 15% overlap | 1203 | semantic | 0.762 | 0.671 | 0.698 |
| 500 chars / 15% overlap | 1203 | keyword | 0.714 | 0.571 | 0.688 |
| 500 chars / 15% overlap | 1203 | hybrid | 0.786 | 0.600 | 0.693 |
| 900 chars / 13% overlap | 810 | semantic **best** | 0.810 | 0.700 | 0.676 |
| 900 chars / 13% overlap | 810 | keyword | 0.619 | 0.557 | 0.656 |
| 900 chars / 13% overlap | 810 | hybrid | 0.714 | 0.600 | 0.662 |

**Chosen setup:** 900 chars / 13% overlap with **semantic** search, starting Top-K = 5.

## Why

This combination placed correct evidence highest on in-scope questions while keeping traces (document, page, section, score).

## Failure case (out of scope)

Query: What insulin dose should be started in a newly diagnosed adult with type 1 diabetes?

No chunk passed the 0.53 confidence gate.
That is the correct Day 2 behavior for out-of-scope questions: retrieve nothing and refuse to generate.

## Quality fixes applied

- Keep diagnostic/recommendation lists in one chunk
- Drop duplicate Top-K hits (same page/section or cosine > 0.92)
- Ignore junk headings such as `(DSM-5)`
- Prefix org / guideline / section before embedding
- Refuse hits below MiniLM cosine 0.53
- Label Precision@K only when the expected source AND a body keyword match

Official demo path: `python main.py --similarity` then `python day2_eval.py`.
Do not use `rag_pipeline_simple.py` for this stage.

## Top-K note

Inspect Top-3, Top-5, and Top-10 on the evidence panel. Use Top-5 as the default: Top-3 misses some paraphrases; Top-10 adds off-section noise.
