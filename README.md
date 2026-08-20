# MindCare

Evidence-based clinical RAG for depression guidelines.

MindCare answers questions from **WHO**, **NICE**, and **USPSTF** PDFs — not from model memory. Every supported claim is cited with `[n]`, linked back to the original guideline, and scored for confidence. The interface supports **English** and **Egyptian Arabic** (مصري). Retrieval always runs in English so the index stays faithful to the source documents.

> **Not a diagnostic tool.** MindCare is educational. It is not a substitute for a clinician, and it does not provide a medical diagnosis.

---

## Features

- **Grounded chat** — hybrid BM25 + MiniLM retrieval, RRF fusion, cross-encoder rerank, then Groq generation with validated `[n]` citations
- **Relevance gate** — `supported` / `insufficient` / `out_of_scope` so off-topic or weakly evidenced questions are refused instead of guessed
- **Source cards** — PDF name, page, chunk, relevance, and a public **Open guideline** URL
- **Egyptian Arabic** — Arabic in → English retrieve → Egyptian Arabic out; screening items stay in published Arabic wording
- **Screening** — PHQ-9, GAD-7, and EPDS, with Egypt crisis guidance (**123**)
- **Voice** — browser speech-to-text and read-aloud (`ar-EG` when the OS has an Egyptian voice)
- **Chat history** — conversation persists when you leave for a screening and come back

---

## How it works

```text
PDF guidelines
    → extract / clean / chunk
    → Chroma (all-MiniLM-L6-v2) + BM25
    → hybrid search → RRF → cross-encoder rerank
    → relevance gate
    → generate with citations → validate [n] → confidence
```

Arabic questions are translated to English **before** search. Answers can be written in Egyptian dialect while citations still point at the English guidelines.

| Status | Meaning |
| --- | --- |
| `supported` | Enough retrieved evidence; answer includes citations |
| `insufficient` | Related to mental health, but the corpus is too weak to answer reliably |
| `out_of_scope` | Outside MindCare’s guideline set |

Without `GROQ_API_KEY`, generation falls back to extractive sentences from the retrieved chunks (English). Dialect answers need Groq.

---

## Project layout

```text
depression-rag-hackathon/          ← run the app from here
  api.py                           FastAPI  (/api/chat, /api/health)
  pipeline.py                      ingest → retrieve → generate
  language.py                      Egyptian Arabic translate / generate
  pdfs/                            WHO, NICE, USPSTF guidelines
  frontend/                        React + Vite UI
  static/                          optional built static UI
  presentation/                    pitch deck and speaker notes
```

The GitHub repository root also contains earlier Day 2 retrieval files (`main.py`, `pdfs/`, `day2_eval.py`). **The product to run is the nested `depression-rag-hackathon/` folder.**

---

## Requirements

- Python 3.10+
- Node.js 18+
- A [Groq](https://console.groq.com/) API key (optional, but required for fluent answers and Egyptian Arabic)

---

## Setup

```powershell
cd depression-rag-hackathon
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `depression-rag-hackathon/.env` (do not commit it):

```env
GROQ_API_KEY=your_key_here
```

```powershell
cd frontend
npm install
```

The first API start **ingests the PDFs** (extract, chunk, embed, BM25). Later starts load the cache from `outputs/`. To rebuild:

```powershell
python main.py --rebuild
```

---

## Run

**Terminal 1 — API** (from `depression-rag-hackathon/`):

```powershell
uvicorn api:app --reload --port 8000
```

**Terminal 2 — UI** (from `depression-rag-hackathon/frontend/`):

```powershell
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to port 8000.

CLI (same folder as `api.py`):

```powershell
python main.py "What are the common symptoms of depression?"
python main.py --language arz
python main.py --eval
```

---

## API

`POST /api/chat`

```json
{
  "message": "What treatments are available for depression?",
  "language": "auto"
}
```

`language`: `en` | `arz` | `auto`

Response includes `answer`, `confidence`, `status`, `sources[]`, and `additional_sources[]`. Each source may include `source_url`.

`GET /api/health` — `{ "status": "ok", "service": "MindCare" }`

---

## Knowledge base

Guidelines in `pdfs/` include WHO depression materials, NICE depression / children / chronic-illness guidance, and USPSTF screening recommendations (depression, anxiety, suicide risk, perinatal). Citation links are mapped in `settings.py` (`SOURCE_URLS`).

---

## Safety

- Screening scores are **not** diagnoses.
- Self-harm items show an in-app crisis notice.
- In Egypt, emergency services: **123**. If you are in immediate danger, go to the nearest emergency department.

---

## License

Hackathon project. Guideline PDFs remain the property of their publishers (WHO, NICE, USPSTF). Use them under their respective terms.
