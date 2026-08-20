# MindCare — business pitch script (5 minutes)

This deck **sells the idea**. The five jury steps are still there, told as a market story — not as a CS lecture.

Use **this** deck for the stage if the room is mixed (ministry, Orange, Creativa, investors). Keep the technical deck as backup for deep Q&A.

Speak as **we / احنا**. Notes on stage are allowed.

---

## Timing

| Slide | Who | Time | Jury step |
|---|---|---|---|
| 1 The idea | A | 0:00–0:15 | Hook |
| 2 The problem | A | 0:15–1:10 | **1. Problem** |
| 3 Who buys it | A | 1:10–1:50 | Business case |
| 4 The concept | A | 1:50–2:30 | Idea they must remember |
| 5 Data + retrieval | B | 2:30–3:20 | **2 + 3** |
| 6 Trust is the product | B | 3:20–4:30 | **4. Hallucination — most important** |
| 7 Proof + GTM + demo | B → operator | 4:30–5:00 | **5. Evaluation & live demo** |
| 8 The ask | after demo / Q&A | — | Close |

If you run long: skip slide 3 details, never skip **6**. The refusal in the demo **is** the business proof.

---

## Slide 1 — The idea (15s) — A

Pause after the first line.

The world’s best depression guidelines already exist. The people who need them cannot use them. So they ask ChatGPT — and ChatGPT guesses.

MindCare puts official NICE, WHO and USPSTF evidence in their hands, in Egyptian Arabic, and stays silent when it is not sure.

**One line:** this is not a therapy bot. This is AI a hospital can deploy.

الفكرة: الدليل موجود. اللي محتاجه مش بيوصل له. احنا بنخلي الوصول آمن.

---

## Slide 2 — The problem (55s) — A

Scene: a GP has a few minutes. The NICE guideline is a book. Egypt has about **one psychiatrist per 100,000 people**. Depression is common (~7% of adults in national studies). In the Eastern Mediterranean region, only a small share of moderate-to-severe cases get treated.

**Medical value:** safer decisions at the front line.  
**Operational value:** multiply scarce specialists — do not replace them.

The real competitor is already in people’s pockets: **ChatGPT**. That is the unsafe default.

بالعربي: المشكلة مش إن مفيش دليل. المشكلة إن الطبيب والمواطن مش بيوصلوا للدليل في الوقت الصح.

---

## Slide 3 — Who buys it (40s) — A

We do not sell “AI”. We sell **safer minutes at the front line**.

1. **Clinics / GPs** — ask the guideline during the visit + PHQ-9 / GAD-7 / EPDS  
2. **Public helplines** — GSMHAT-style agents; cited Arabic or a clean refusal  
3. **Telco / digital health** — Orange is in the room. They need a wellness channel that will not invent medical advice

B2B / B2G license per seat or per channel. We do not put ads on sad users. We do not compete with psychiatrists.

---

## Slide 4 — The concept (40s) — A

The sentence they must leave with:

**We cite the page, or we do not speak.**

Ask → ground in official PDFs → prove with a page → protect by staying silent.

Without us: ChatGPT or a closed PDF.  
With us: bilingual, cited, refuse-when-unsure, screening in the same app.

---

## Slide 5 — How it works (50s) — B

Jury steps 2 and 3, in business English.

**In:** 12 official PDFs only (NICE, WHO, USPSTF). Clean, chunk, tag with page + URL. **848** passages. A legal team can name every document we are allowed to know.

**Out:** Arabic question is searched against the guideline language. Keyword search catches drug names and PHQ-9. Meaning search catches “I feel empty”. The best passages are fused and reranked. **Only then** is an answer allowed.

Do not say BM25 / RRF unless they ask.

---

## Slide 6 — Trust is the product (70s) — B

**Slow down.** Fluency is cheap. Trust is what a ministry will buy.

1. Grounded by design — no outside knowledge  
2. Citation firewall — fake `[7]` is deleted in code  
3. Evidence bar — weak match, no generation (threshold 2.0)  
4. Hard refuse — off-topic, confidence 0  
5. Honest uncertainty — real question, thin evidence → “not enough in the documents”  
6. Audit trail — PDF, page, link; confidence from retrieval, not from the model

Would Orange put their logo on ChatGPT medical answers? No. That is why this exists.

الوزارة مش هتشتري كلام طليق. هتشتري نظام مسموح له يقول مش عارف.

---

## Slide 7 — Proof, GTM, demo (30s then UI)

We measure Recall / Precision@5. Off-topic must return nothing. The app is already a product: bilingual, voice, screening.

**Path:** clinics now → helpline / primary-care pilot next → Orange and MENA scale.

Then stop talking. Open the UI.

1. `What does NICE recommend for moderate depression in adults?` → point at the page  
2. `What is the capital of France?` → **must refuse** (this is the business)  
3. `إيه أعراض الاكتئاب؟`  
4. If time: PHQ-9 → Ask the guideline about this score  

---

## Slide 8 — The ask (after demo)

Do not fund another chatbot. Fund the layer Egypt can actually deploy.

- Ministry / Creativa: a helpline or primary-care **pilot**  
- Orange / investors: **distribution**  
- Clinics / universities: **use it this semester**

Last line, then silence: **We cite the page. Or we do not speak.**

---

## If they push on numbers

- Psychiatrist density: order of **~1 per 100,000** (WHO / national reports; do not pretend it is a live census).  
- Adult depression: national literature ~**6.8%** as the most common psychiatric diagnosis.  
- Treatment coverage: WHO EMR historically **~3.6%** for moderate–severe depression; global minimally adequate treatment **~9.1%** (Atlas 2024).  
- Say “studies show / on the order of” — do not over-claim.

Revenue if asked: seat license for clinics; channel license for helplines and telcos. Public pilot can be subsidised. Patients are not the customer.
