"""
MindCare web API — serves the RAG chat endpoint and the built frontend.
"""

from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline import load_or_build_index, ask

app = FastAPI(title="MindCare API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_index = None


def get_index():
    global _index
    if _index is None:
        _index = load_or_build_index()
    return _index


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


def format_sources(results) -> list[dict]:
    """Deduplicate by source file, keeping the best relevance score per document."""
    seen: dict[str, dict] = {}
    for result in results:
        meta = result.get("metadata", {})
        source = meta.get("source_file", "unknown source")
        rerank = result.get("rerank_score")
        fused = result.get("fused_score")
        score = rerank if rerank is not None else fused

        if source not in seen or (score is not None and (seen[source]["relevance_score"] or 0) < score):
            seen[source] = {
                "name": prettify_source_name(source),
                "relevance_score": round(score, 3) if score is not None else None,
                "page": meta.get("page_number"),
            }
    return list(seen.values())


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class SourceItem(BaseModel):
    name: str
    relevance_score: float | None = None
    page: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "MindCare"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        index = get_index()
        answer, results = ask(index, request.message.strip(), n_results=5)
        sources = format_sources(results)
        return ChatResponse(answer=answer, sources=sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
