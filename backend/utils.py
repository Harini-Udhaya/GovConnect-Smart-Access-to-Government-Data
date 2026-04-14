"""
GovConnect – Utility Functions
Covers: PDF extraction, chunking, embedding, FAISS, Groq LLM
"""

import io
import numpy as np
from typing import List, Dict, Any

# ── Globals (in-memory store) ──────────────────────────────────────────────

_embedder = None          # SentenceTransformer singleton
_faiss_index = None       # FAISS index
_chunks: List[str] = []   # Parallel chunk texts
_chunk_meta: List[str] = []  # Parallel doc names


# ── Embedder ───────────────────────────────────────────────────────────────

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


# ── PDF Extraction ─────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(parts)


# ── Chunking ───────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


# ── FAISS Index ────────────────────────────────────────────────────────────

def _build_or_update_index(embeddings: np.ndarray):
    """Rebuild a fresh inner-product (cosine) FAISS index over all chunks."""
    import faiss
    global _faiss_index

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    norm_emb = embeddings.copy()
    faiss.normalize_L2(norm_emb)
    index.add(norm_emb)
    _faiss_index = index


def add_to_index(embedder, chunks: List[str], doc_name: str) -> int:
    global _chunks, _chunk_meta, _faiss_index

    _chunks.extend(chunks)
    _chunk_meta.extend([doc_name] * len(chunks))

    # Re-embed everything (simple; avoids index dimension mismatch)
    all_embs = embedder.encode(_chunks, normalize_embeddings=True, show_progress_bar=False)
    _build_or_update_index(np.array(all_embs, dtype=np.float32))

    return len(chunks)


def get_index_stats() -> Dict[str, Any]:
    docs = list(set(_chunk_meta))
    return {
        "total_chunks": len(_chunks),
        "total_documents": len(docs),
        "documents": docs,
    }


def reset_index():
    global _chunks, _chunk_meta, _faiss_index
    _chunks = []
    _chunk_meta = []
    _faiss_index = None


# ── Semantic Search ────────────────────────────────────────────────────────

def semantic_search(
    embedder,
    query: str,
    top_k: int = 5,
    threshold: float = 0.75,
):
    import faiss

    if _faiss_index is None or len(_chunks) == 0:
        print("DEBUG: Index is empty ❌")
        return []

    print("\n================ DEBUG START ================")
    print("Query:", query)

    q_emb = embedder.encode([query], normalize_embeddings=True)
    q_arr = np.array(q_emb, dtype=np.float32)
    faiss.normalize_L2(q_arr)

    scores, indices = _faiss_index.search(q_arr, min(top_k, len(_chunks)))

    print("\nTop FAISS Results (before filtering):")

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        print(f"\nScore: {score:.4f}")
        print("Doc:", _chunk_meta[idx])
        print("Chunk Preview:", _chunks[idx][:200])

        if float(score) < threshold:
            print("❌ Rejected due to threshold")
            continue

        print("✅ Accepted")

        results.append({
            "chunk": _chunks[idx],
            "doc": _chunk_meta[idx],
            "score": float(score),
        })

    print("================ DEBUG END =================\n")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ── Groq LLM ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are GovConnect, an AI assistant for government policy documents.

RULES:
1. Answer ONLY using the provided context.
2. Provide a CLEAR and SHORT explanation (2–4 sentences).
3. Summarize the information instead of listing multiple rules.
4. Do NOT copy large chunks of text directly.
5. Only include key points relevant to the question.
6. If no relevant info exists, say:
   "The requested information is not available in the provided documents."
"""


def ask_groq(api_key: str, context_chunks: List[Dict], query: str) -> str:
    from groq import Groq

    context_text = "\n\n---\n\n".join(
    f"[Document: {c['doc']}]\n{c['chunk'][:800]}"  # limit chunk size
    for c in context_chunks[:3]  # only top 3 chunks
)

    user_msg = f"""Context from policy documents:

{context_text}

---

Question: {query}

Answer (only from the context above):"""

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
    model="llama-3.1-8b-instant",  # ✅ WORKING MODEL
    messages=[
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ],
    temperature=0.1,
    max_tokens=700,
)
    return resp.choices[0].message.content.strip()
