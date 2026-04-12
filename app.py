import os
import json
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)

UPLOAD_DIR = Path("uploads")
VECTOR_DIR = Path("vector_store")
UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_DIR.mkdir(exist_ok=True)

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80
TOP_K = 5
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"

vector_store = {
    "embeddings": None,
    "chunks": [],
    "metadata": [],
}

def get_openai_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)

def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract text with page numbers from a PDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages.append({"page": page_num + 1, "text": text})
        doc.close()
        return pages
    except ImportError:
        pass

    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page": page_num + 1, "text": text})
        return pages
    except ImportError:
        raise ImportError("Install either PyMuPDF (fitz) or pdfplumber: pip install pymupdf pdfplumber")

def chunk_text(pages: list[dict], filename: str) -> list[dict]:
    """Split page text into overlapping chunks with metadata."""
    chunks = []
    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]
        words = text.split()
        i = 0
        chunk_idx = 0
        while i < len(words):
            chunk_words = words[i: i + CHUNK_SIZE]
            chunk_text_str = " ".join(chunk_words)
            if len(chunk_text_str.strip()) > 50:
                chunks.append({
                    "text": chunk_text_str,
                    "source": filename,
                    "page": page_num,
                    "chunk_id": f"{filename}_p{page_num}_c{chunk_idx}",
                })
                chunk_idx += 1
            i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def get_embeddings(texts: list[str]) -> np.ndarray:
    """Get embeddings for a list of texts using OpenAI."""
    client = get_openai_client()
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
    return np.array(all_embeddings, dtype=np.float32)

def cosine_similarity_search(query_embedding: np.ndarray, embeddings: np.ndarray, top_k: int) -> list[int]:
    """Simple cosine similarity search without FAISS dependency."""
    query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10
    normed = embeddings / norms
    similarities = normed @ query_norm
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return top_indices.tolist()

def save_vector_store():
    store_path = VECTOR_DIR / "store.pkl"
    with open(store_path, "wb") as f:
        pickle.dump(vector_store, f)
    logger.info(f"Vector store saved: {len(vector_store['chunks'])} chunks")

def load_vector_store():
    global vector_store
    store_path = VECTOR_DIR / "store.pkl"
    if store_path.exists():
        with open(store_path, "rb") as f:
            vector_store = pickle.load(f)
        logger.info(f"Vector store loaded: {len(vector_store['chunks'])} chunks")
    else:
        logger.info("No existing vector store found, starting fresh")

def add_to_vector_store(chunks: list[dict]):
    """Embed chunks and add to the in-memory vector store."""
    global vector_store
    texts = [c["text"] for c in chunks]
    logger.info(f"Embedding {len(texts)} chunks...")
    new_embeddings = get_embeddings(texts)

    if vector_store["embeddings"] is None:
        vector_store["embeddings"] = new_embeddings
    else:
        vector_store["embeddings"] = np.vstack([vector_store["embeddings"], new_embeddings])

    vector_store["chunks"].extend(chunks)
    save_vector_store()

def search_vector_store(query: str, top_k: int = TOP_K) -> list[dict]:
    """Search the vector store and return top-k relevant chunks."""
    if vector_store["embeddings"] is None or len(vector_store["chunks"]) == 0:
        return []

    query_emb = get_embeddings([query])[0]
    indices = cosine_similarity_search(query_emb, vector_store["embeddings"], top_k)

    results = []
    seen_sources = {}
    for idx in indices:
        chunk = vector_store["chunks"][idx]
        key = (chunk["source"], chunk["page"])
        if key not in seen_sources:
            seen_sources[key] = True
            results.append(chunk)
    return results

def build_prompt(query: str, context_chunks: list[dict]) -> list[dict]:
    """Build the messages list for the LLM."""
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['source']}, Page {chunk['page']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """You are GovQuery, an AI-powered policy helpdesk for Indian government employees.

Your role is to answer questions about government service rules, leave policies, pension guidelines, and administrative procedures using ONLY the provided policy document context.

Guidelines:
- Answer clearly and concisely in plain language
- Always cite the specific source document and page number
- If the context doesn't contain enough information, say so honestly
- Do not make up rules or cite rules not present in the context
- Structure longer answers with numbered points when appropriate
- Be precise about rule numbers and circular references when present"""

    user_message = f"""Context from official policy documents:

{context}

---

Employee question: {query}

Please provide a clear, accurate answer based on the above context. At the end of your answer, include a "Sources:" section listing the document names and page numbers you referenced."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/status")
def status():
    doc_names = list(set(c["source"] for c in vector_store["chunks"]))
    return jsonify({
        "status": "ready",
        "chunks_indexed": len(vector_store["chunks"]),
        "documents": doc_names,
        "has_documents": len(vector_store["chunks"]) > 0,
    })

@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    filename = file.filename
    file_path = UPLOAD_DIR / filename

    already_indexed = any(c["source"] == filename for c in vector_store["chunks"])
    if already_indexed:
        return jsonify({
            "success": True,
            "message": f"'{filename}' is already indexed.",
            "filename": filename,
            "chunks_added": 0,
        })

    file.save(str(file_path))
    logger.info(f"Saved: {file_path}")

    try:
        pages = extract_text_from_pdf(file_path)
        if not pages:
            return jsonify({"error": "Could not extract text from PDF. The file may be scanned/image-based."}), 400

        chunks = chunk_text(pages, filename)
        if not chunks:
            return jsonify({"error": "No text chunks could be created from the PDF."}), 400

        add_to_vector_store(chunks)

        return jsonify({
            "success": True,
            "message": f"Successfully indexed '{filename}'",
            "filename": filename,
            "pages_processed": len(pages),
            "chunks_added": len(chunks),
        })

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        if file_path.exists():
            file_path.unlink()
        return jsonify({"error": str(e)}), 500

@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "No query provided"}), 400

    user_query = data["query"].strip()
    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    if len(vector_store["chunks"]) == 0:
        return jsonify({
            "error": "No documents have been uploaded yet. Please upload PDF documents first."
        }), 400

    try:
        context_chunks = search_vector_store(user_query, top_k=TOP_K)
        if not context_chunks:
            return jsonify({
                "answer": "I could not find relevant information in the uploaded documents for your query.",
                "sources": [],
            })

        messages = build_prompt(user_query, context_chunks)
        client = get_openai_client()
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=1200,
        )
        answer = response.choices[0].message.content

        sources = []
        seen = set()
        for chunk in context_chunks:
            key = (chunk["source"], chunk["page"])
            if key not in seen:
                seen.add(key)
                sources.append({
                    "document": chunk["source"],
                    "page": chunk["page"],
                    "excerpt": chunk["text"][:280] + "..." if len(chunk["text"]) > 280 else chunk["text"],
                })

        return jsonify({
            "answer": answer,
            "sources": sources,
        })

    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Invalid or missing OpenAI API key. Please set the OPENAI_API_KEY environment variable."
        return jsonify({"error": error_msg}), 500

@app.route("/api/clear", methods=["POST"])
def clear_documents():
    global vector_store
    vector_store = {"embeddings": None, "chunks": [], "metadata": []}
    store_path = VECTOR_DIR / "store.pkl"
    if store_path.exists():
        store_path.unlink()
    for f in UPLOAD_DIR.glob("*.pdf"):
        f.unlink()
    return jsonify({"success": True, "message": "All documents cleared."})

if __name__ == "__main__":
    load_vector_store()
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting GovQuery on http://localhost:{port}")
    app.run(debug=False, port=port, host="0.0.0.0")
