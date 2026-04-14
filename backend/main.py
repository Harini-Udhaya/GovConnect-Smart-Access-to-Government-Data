"""
GovConnect – AI Policy Helpdesk
Backend: FastAPI + FAISS + sentence-transformers + Groq
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os

from utils import (
    extract_text_from_pdf,
    chunk_text,
    get_embedder,
    add_to_index,
    semantic_search,
    ask_groq,
    get_index_stats,
    reset_index,
)

app = FastAPI(title="GovConnect API", version="1.0.0")

# Allow frontend (any origin during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    groq_api_key: str


class SourceChunk(BaseModel):
    text: str
    document: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "GovConnect API is running"}


@app.get("/stats")
def stats():
    """Return current index statistics."""
    return get_index_stats()


@app.post("/reset")
def reset():
    """Clear the FAISS index and all stored chunks."""
    reset_index()
    return {"status": "ok", "message": "Index reset successfully"}


@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Accept PDF uploads, extract text, chunk, embed, store in FAISS.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    embedder = get_embedder()

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"file": file.filename, "status": "skipped", "reason": "not a PDF"})
            continue

        raw_bytes = await file.read()

        try:
            text = extract_text_from_pdf(raw_bytes)
        except Exception as e:
            results.append({"file": file.filename, "status": "error", "reason": str(e)})
            continue

        if not text.strip():
            results.append({"file": file.filename, "status": "error", "reason": "no extractable text"})
            continue

        chunks = chunk_text(text)
        if not chunks:
            results.append({"file": file.filename, "status": "error", "reason": "no chunks generated"})
            continue

        n_added = add_to_index(embedder, chunks, file.filename)
        results.append({
            "file": file.filename,
            "status": "success",
            "chunks_indexed": n_added,
        })

    return {"results": results, "index_stats": get_index_stats()}


@app.post("/query", response_model=QueryResponse)
def query_documents(req: QueryRequest):
    """
    Semantic search + LLM answer generation.
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if not req.groq_api_key:
        raise HTTPException(status_code=400, detail="Groq API key is required")

    stats = get_index_stats()
    if stats["total_chunks"] == 0:
        return QueryResponse(
            answer="The requested information is not available in the provided documents.",
            sources=[],
        )

    embedder = get_embedder()

    # Semantic retrieval
    results = semantic_search(
        embedder=embedder,
        query=f"Explain in government rules: {question}",
        top_k=3,
        threshold=0.4,
    )

    if not results:
        return QueryResponse(
            answer="The requested information is not available in the provided documents.",
            sources=[],
        )

    # LLM answer
    try:
        answer = ask_groq(
            api_key=req.groq_api_key,
            context_chunks=results,
            query=question,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

    sources = [
        SourceChunk(text=r["chunk"], document=r["doc"], score=round(r["score"], 4))
        for r in results
    ]

    return QueryResponse(answer=answer, sources=sources)
