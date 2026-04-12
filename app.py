"""
GovQuery — AI Policy Helpdesk
Free stack: Groq (LLaMA 3) for LLM + sentence-transformers (local) for embeddings
Fallback: TF-IDF embeddings if sentence-transformers not yet downloaded
"""

import os
import pickle
import logging
import warnings
from pathlib import Path

import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)

UPLOAD_DIR = Path("uploads")
VECTOR_DIR = Path("vector_store")
UPLOAD_DIR.mkdir(exist_ok=True)
VECTOR_DIR.mkdir(exist_ok=True)

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 60
TOP_K         = 5
GROQ_MODEL    = "llama3-8b-8192"
EMBED_MODEL   = "all-MiniLM-L6-v2"

_embed_fn   = None
_st_model   = None
_tfidf_vec  = None
_embed_mode = "none"

vector_store = {"embeddings": None, "chunks": []}


def _try_load_sentence_transformers():
    global _st_model, _embed_fn, _embed_mode
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading '{EMBED_MODEL}' (first run downloads ~90 MB)...")
        _st_model   = SentenceTransformer(EMBED_MODEL)
        _embed_fn   = _st_embed
        _embed_mode = "st"
        logger.info("sentence-transformers ready.")
        return True
    except Exception as e:
        logger.warning(f"sentence-transformers unavailable ({e}). Using TF-IDF fallback.")
        return False


def _st_embed(texts):
    return _st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def _tfidf_embed(texts):
    global _tfidf_vec
    if _tfidf_vec is None:
        all_texts = [c["text"] for c in vector_store["chunks"]] + list(texts)
        from sklearn.feature_extraction.text import TfidfVectorizer
        _tfidf_vec = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
        _tfidf_vec.fit(all_texts)
        logger.info("TF-IDF vectoriser fitted.")
    return _tfidf_vec.transform(texts).toarray().astype(np.float32)


def _rebuild_tfidf():
    global _tfidf_vec
    if _embed_mode != "tfidf" or not vector_store["chunks"]:
        return
    texts = [c["text"] for c in vector_store["chunks"]]
    from sklearn.feature_extraction.text import TfidfVectorizer
    _tfidf_vec = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    vecs = _tfidf_vec.fit_transform(texts).toarray().astype(np.float32)
    vector_store["embeddings"] = vecs
    logger.info(f"TF-IDF rebuilt on {len(texts)} chunks.")


def get_embeddings(texts):
    return _embed_fn(texts)


def save_vector_store():
    with open(VECTOR_DIR / "store.pkl", "wb") as f:
        pickle.dump({"chunks": vector_store["chunks"],
                     "embeddings": vector_store["embeddings"],
                     "embed_mode": _embed_mode}, f)
    logger.info(f"Saved {len(vector_store['chunks'])} chunks.")


def load_vector_store():
    path = VECTOR_DIR / "store.pkl"
    if not path.exists():
        return
    with open(path, "rb") as f:
        data = pickle.load(f)
    vector_store["chunks"]     = data.get("chunks", [])
    vector_store["embeddings"] = data.get("embeddings", None)
    logger.info(f"Loaded {len(vector_store['chunks'])} chunks.")


def cosine_search(q_vec, matrix, top_k):
    q = q_vec / (np.linalg.norm(q_vec) + 1e-10)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    sims  = (matrix / norms) @ q
    return np.argsort(sims)[::-1][:top_k].tolist()


def add_chunks_to_store(chunks):
    if _embed_mode == "tfidf":
        vector_store["chunks"].extend(chunks)
        _rebuild_tfidf()
    else:
        new_embs = get_embeddings([c["text"] for c in chunks])
        if vector_store["embeddings"] is None:
            vector_store["embeddings"] = new_embs
        else:
            vector_store["embeddings"] = np.vstack([vector_store["embeddings"], new_embs])
        vector_store["chunks"].extend(chunks)
    save_vector_store()


def search(query, top_k=TOP_K):
    if not vector_store["chunks"] or vector_store["embeddings"] is None:
        return []
    q_vec   = (_tfidf_embed if _embed_mode == "tfidf" else get_embeddings)([query])[0]
    indices = cosine_search(q_vec, vector_store["embeddings"], top_k * 2)
    seen, results = set(), []
    for i in indices:
        c   = vector_store["chunks"][i]
        key = (c["source"], c["page"])
        if key not in seen:
            seen.add(key)
            results.append(c)
        if len(results) >= top_k:
            break
    return results


def extract_pdf(path):
    try:
        import fitz
        doc, pages = fitz.open(str(path)), []
        for i in range(len(doc)):
            text = doc[i].get_text()
            if text.strip():
                pages.append({"page": i + 1, "text": text})
        doc.close()
        return pages
    except Exception:
        pass
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, pg in enumerate(pdf.pages):
            text = pg.extract_text() or ""
            if text.strip():
                pages.append({"page": i + 1, "text": text})
    return pages


def make_chunks(pages, filename):
    chunks = []
    for pg in pages:
        words = pg["text"].split()
        i, idx = 0, 0
        while i < len(words):
            chunk = " ".join(words[i: i + CHUNK_SIZE])
            if len(chunk.strip()) > 40:
                chunks.append({"text": chunk, "source": filename,
                                "page": pg["page"],
                                "chunk_id": f"{filename}_p{pg['page']}_c{idx}"})
                idx += 1
            i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def generate_answer(query, chunks):
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "GROQ_API_KEY not set.\n"
            "Get a free key at https://console.groq.com then run:\n"
            "  export GROQ_API_KEY=gsk_..."
        )
    context = "\n\n---\n\n".join(
        f"[Source: {c['source']} | Page {c['page']}]\n{c['text']}" for c in chunks
    )
    from groq import Groq
    client = Groq(api_key=key)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": (
                "You are GovQuery, an AI policy helpdesk for Indian government employees. "
                "Answer using ONLY the provided document context. "
                "Be clear and concise. Use numbered points for multi-part answers. "
                "Always cite the source document and page. "
                "End with a 'Sources:' section. "
                "If context lacks info, say so — never invent rules."
            )},
            {"role": "user", "content": (
                f"Context:\n\n{context}\n\n---\n\nQuestion: {query}\n\n"
                "Answer based only on the above context."
            )},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    return resp.choices[0].message.content


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def status():
    docs = list(set(c["source"] for c in vector_store["chunks"]))
    return jsonify({
        "status": "ready",
        "chunks_indexed": len(vector_store["chunks"]),
        "documents": docs,
        "has_documents": bool(docs),
        "embed_mode": _embed_mode,
        "llm_model": GROQ_MODEL,
    })


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400
    filename  = file.filename
    file_path = UPLOAD_DIR / filename
    if any(c["source"] == filename for c in vector_store["chunks"]):
        return jsonify({"success": True, "message": f"'{filename}' already indexed.",
                        "filename": filename, "chunks_added": 0})
    file.save(str(file_path))
    try:
        pages = extract_pdf(file_path)
        if not pages:
            file_path.unlink(missing_ok=True)
            return jsonify({"error": "No text extracted — PDF may be image/scanned."}), 400
        chunks = make_chunks(pages, filename)
        if not chunks:
            file_path.unlink(missing_ok=True)
            return jsonify({"error": "Could not create text chunks."}), 400
        add_chunks_to_store(chunks)
        return jsonify({"success": True, "message": f"Indexed '{filename}'",
                        "filename": filename, "pages_processed": len(pages),
                        "chunks_added": len(chunks)})
    except Exception as e:
        logger.error(e, exc_info=True)
        file_path.unlink(missing_ok=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json() or {}
    q    = data.get("query", "").strip()
    if not q:
        return jsonify({"error": "Query cannot be empty"}), 400
    if not vector_store["chunks"]:
        return jsonify({"error": "No documents indexed yet. Upload PDFs first."}), 400
    try:
        chunks = search(q)
        if not chunks:
            return jsonify({"answer": "No relevant information found in uploaded documents.",
                            "sources": []})
        answer  = generate_answer(q, chunks)
        sources, seen = [], set()
        for c in chunks:
            key = (c["source"], c["page"])
            if key not in seen:
                seen.add(key)
                excerpt = c["text"][:280] + ("..." if len(c["text"]) > 280 else "")
                sources.append({"document": c["source"], "page": c["page"], "excerpt": excerpt})
        return jsonify({"answer": answer, "sources": sources})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(e, exc_info=True)
        msg = str(e)
        if any(w in msg.lower() for w in ["api", "auth", "key", "groq"]):
            msg = "Groq API key error — set GROQ_API_KEY environment variable."
        return jsonify({"error": msg}), 500


@app.route("/api/clear", methods=["POST"])
def clear():
    global _tfidf_vec
    vector_store["embeddings"] = None
    vector_store["chunks"]     = []
    _tfidf_vec = None
    (VECTOR_DIR / "store.pkl").unlink(missing_ok=True)
    for f in UPLOAD_DIR.glob("*.pdf"):
        f.unlink()
    return jsonify({"success": True, "message": "All documents cleared."})


def startup():
    global _embed_fn, _embed_mode
    if not _try_load_sentence_transformers():
        _embed_fn   = _tfidf_embed
        _embed_mode = "tfidf"
        logger.info("TF-IDF mode active — no internet or model download needed.")
    load_vector_store()
    if vector_store["chunks"] and _embed_mode == "tfidf":
        _rebuild_tfidf()


if __name__ == "__main__":
    startup()
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"GovQuery → http://localhost:{port}  |  embed={_embed_mode}  |  llm={GROQ_MODEL}")
    app.run(debug=False, host="0.0.0.0", port=port)
