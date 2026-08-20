# MindCare — 5-minute pitch script

Follow the jury order. **Max 5 minutes**, then discussion. Speak as **we / احنا**, never “I”.

**Roles (2 speakers + laptop operator)**
- **Speaker A:** title, problem, data ingestion, then stays for demo questions
- **Speaker B:** retrieval, hallucination/citations, evaluation, then hands to demo
- **Operator:** never jumps slides unless a speaker points. After slide 7, **open the Web UI and do not go back**.

Dress: formal / semi-formal. Notes on stage are allowed.

---

## Timing

| Slide | Who | Time |
|---|---|---|
| 1 Title | A | 0:00–0:10 |
| 2 Problem | A | 0:10–1:05 |
| 3 Data ingestion | A | 1:05–1:50 |
| 4 Retrieval | B | 1:50–2:35 |
| 5 Hallucination (most important) | B | 2:35–3:50 |
| 6 Citation example | B | 3:50–4:10 |
| 7 Evaluation → demo | B then operator | 4:10–5:00 |
| 8 Product extras | skip unless Q&A | — |
| 9 Close | only if demo is blocked | — |

If you are over time, **skip slide 6 and 8**. Never skip slide 5.

---

## Slide 1 — Title (10s) — Speaker A

We built **MindCare**: a clinical RAG assistant for depression. It answers only from official NICE, WHO, and USPSTF guidelines — and it is designed so the model cannot invent medical facts.

احنا عملنا MindCare: مساعد طبي بيرد من الإرشادات الرسمية بس، ومن غير تخمين.

---

## Slide 2 — Problem (50s) — Speaker A

One problem: **clinicians cannot safely ask a general LLM about depression.**

1. Official guidelines exist, but they are hundreds of pages. Nobody can search them at the bedside.
2. A generic LLM will invent dosages, mix adult and child pathways, and cite pages that do not exist. In mental health that is a **safety failure**.
3. In Egypt there is also a language gap: evidence is English; staff and families need **المصري**.

**Medical value:** cited answers from NICE / WHO / USPSTF.  
**Operational value:** bilingual UI, PHQ-9 / GAD-7 / EPDS screening, and a **refuse-to-answer** path.  
This is decision support — not a chatbot that plays doctor.

---

## Slide 3 — Data ingestion (45s) — Speaker A

We did **not** scrape the web. We ingested **12 official PDFs**:

- **NICE:** NG222 adults treatment, NG134 children, QS8, QS48, CG91 chronic illness
- **WHO EMRO** clinical guides
- **USPSTF** depression, suicide, anxiety, perinatal screening

Pipeline: extract page text → clean footers, URLs, boilerplate → recursive chunks **1000 / overlap 150** → metadata: **file, page, chunk, public URL**.

**848 chunks**, indexed in Chroma (MiniLM) + BM25, cached so the demo starts in seconds.

---

## Slide 4 — Retrieval (45s) — Speaker B

The LLM never searches. Retrieval builds the evidence pack first.

Arabic is translated for search. Then:

1. **BM25** — exact terms (PHQ-9, fluoxetine, NG222)
2. **Semantic search** — paraphrases (“feeling hopeless”)
3. **Reciprocal Rank Fusion** — chunks found by both paths rise
4. **Cross-encoder rerank** — “does this passage actually answer this question?”
5. **Top 5 chunks** go to generation, each with source + page

---

## Slide 5 — Hallucination prevention (70s) — Speaker B

**Slow down. This is the slide they asked for.**

Six locks:

1. **Grounded prompt**, temperature 0: answer only from numbered passages. No outside knowledge.
2. **Citation firewall:** any `[n]` that was not retrieved is **deleted in code**.
3. **Relevance gate:** rerank score must be **≥ 2.0**. Below that we do not generate.
4. **Out of scope:** capital cities, recipes, code → no answer, confidence 0.
5. **Insufficient evidence:** mental-health question but weak chunks → we say we cannot answer reliably.
6. **Page-level proof:** PDF name, page, chunk, relevance, official URL.

If the model produces no valid citation, we fall back to an **extractive** snippet from the top chunk — still cited.

النقطة الأهم: الـ LLM مش حر. لو الدليل مش كفاية أو السؤال برة النطاق، السيستم بيرفض.

---

## Slide 6 — Citation example (20s) — Speaker B

Every sentence has a `[n]`. Each `[n]` maps to a real PDF page. Invalid IDs never reach the user.

---

## Slide 7 — Evaluation + live demo (50s) — Speaker B then operator

We measure:

- **Precision@k** and **Recall@5** on clinical test queries (did the right guideline appear?)
- **Guardrail:** threshold 2.0; out-of-scope should return nothing
- **Confidence:** formula on retrieval + citation coverage — **never** “the model says it is sure”

Then: **“Let us show it live.” Stop talking. Open the UI.**

---

## Live demo — operator checklist

Have the app already running before you walk on stage.

**Q1 — on topic (English)**  
`What treatments does NICE recommend for moderate depression in adults?`  
Point at `[1]`, page number, “Open guideline”.

**Q2 — out of scope**  
`What is the capital of France?`  
Must refuse. Confidence 0. No fake medical answer.

**Q3 — Arabic**  
`إيه أعراض الاكتئاب؟`  
Egyptian Arabic answer, same citation cards.

**Q4 — screening (if time)**  
Open **PHQ-9** → fill quickly → Calculate → **Ask the guideline about this score**.

**Voice (bonus, if time)**  
Click Speak, ask one short English question, enable auto-read.

Do **not** type slowly. Paste from this list if needed.

---

## Likely jury questions (rest of the team answers)

| Question | Answer in one sentence |
|---|---|
| Why hybrid search? | Keywords catch drug/instrument names; embeddings catch paraphrases; fusion + rerank keep both. |
| How do you stop hallucination? | Retrieval first, temperature 0, citation validation, score threshold 2.0, refuse if weak or off-topic. |
| What if the LLM cites `[9]`? | We strip any ID not in the retrieved set before the UI sees it. |
| Why not a bigger model? | Safety is in the evidence layer, not in model size. |
| Is this a diagnosis? | No. Educational / decision-support, with a crisis path on PHQ-9 item 9. |
| Arabic quality? | Question is translated for retrieval; answer can be generated or localized in Egyptian Arabic. |
| Can this go to market? | Yes as a clinic/helpline copilot on top of official guidelines — not as a replacement for a psychiatrist. |
| Project structure? | Separate modules: ingest, retrieval, relevance, generation, citations, confidence, FastAPI, React. |

---

## Before you go on stage

1. Run the frontend and API. Test all four demo questions.
2. Optional: `python main.py --eval` and write Precision@5 / Recall@5 on a sticky note for Q&A.
3. Browser zoom 125%. Chat tab open. Language = EN first.
4. Close Slack / email. Full screen.
5. Operator sits at the laptop; speakers stand.
