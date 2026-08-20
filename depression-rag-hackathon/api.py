"""
MindCare web API — serves the RAG chat endpoint and the built frontend.
"""

from pathlib import Path

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


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(
        default="auto",
        description="en, arz (Egyptian Arabic), or auto to detect from the message.",
    )


class SourceItem(BaseModel):
    citation_id: int
    pdf: str
    name: str
    page: int | None = None
    chunk: int | None = None
    relevance_score: float | None = None
    source_url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    status: str
    sources: list[SourceItem]
    additional_sources: list[SourceItem] = []


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "MindCare"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        index = get_index()
        result = ask(
            index,
            request.message.strip(),
            n_results=5,
            language=request.language,
        )
        return ChatResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            status=result["status"],
            sources=result["sources"],
            additional_sources=result.get("additional_sources", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
