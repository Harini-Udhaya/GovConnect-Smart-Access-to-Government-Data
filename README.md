# ⚡ GovConnect — AI Policy Helpdesk

A **full-stack AI-powered policy assistant** that enables government employees to query official documents using **semantic search + LLM intelligence**.

🧠 No keyword matching — only context-aware, document-grounded answers.

---

## 🤖 About the Project

GovConnect uses a **Retrieval-Augmented Generation (RAG)** architecture.

- Retrieves relevant content from uploaded documents using **FAISS + embeddings**
- Generates answers using **Groq LLM**
- Ensures responses are grounded strictly in documents (no hallucination)

---

## ✨ Key Features

- 🔍 **Semantic Search (FAISS)** — understands meaning, not keywords  
- 🤖 **AI-Powered Answers (Groq LLM)** — accurate & context-based  
- 📄 **PDF Document Support** — upload multiple policy files  
- 🔗 **Source Transparency** — shows exact document references  
- 🎯 **Hallucination Control** — answers only from documents  
- ⚡ **Local Embeddings** — fast and cost-efficient  

---

## 🖥️ Demo Preview

- Ask a question  
- Relevant document chunks are retrieved  
- AI generates a concise answer  
- Sources are displayed for verification  

---

## 🗂️ Project Structure

govconnect/
├── backend/
│ ├── main.py # FastAPI backend
│ └── utils.py # AI + FAISS + PDF logic
├── frontend/
│ ├── index.html # UI
│ ├── styles.css # Styling
│ └── script.js # Logic
├── assets/
│ ├── chat_ui.png
│ ├── upload_section.png
│ └── sources_view.png
├── sample_documents/ # Sample PDFs for testing
├── requirements.txt
└── README.md

---

## 🚀 Quick Start

1️⃣ Install Dependencies
bash
pip install -r requirements.txt
⚠️ First run downloads embedding model (~90MB)

2️⃣ Get Groq API Key
👉 https://console.groq.com

3️⃣ Run Backend
cd backend
uvicorn main:app --reload --port 8000
📍 http://localhost:8000
📍 http://localhost:8000/docs

4️⃣ Run Frontend
Open:
frontend/index.html

🌐 Live Deployment
Frontend: https://govconnect-helpdesk-chatbot.vercel.app/
Backend: https://govconnect-backend-5jf3.onrender.com

⚠️ Important Note for Evaluation
The backend is deployed on Render (free tier), which has:
Cold start delay (30–60 seconds)
Limited CPU and memory
Timeout for heavy AI tasks
Since this project uses embedding models + FAISS, document indexing may be slow or fail on live deployment.

💡 Recommended Way to Test (BEST EXPERIENCE)

Run locally for smooth performance:
cd backend
uvicorn main:app --reload

Update in script.js:
const API_BASE = "http://localhost:8000";

✅ Fast indexing
✅ Instant responses
✅ Full functionality

📂 Demo Instructions
1. Upload Documents
Use files from:
sample_documents/

2. Ask Questions
Sample Queries
- What is lien?
- Explain earned leave
- What are the conditions for pension eligibility?
- What is leave encashment?
- How are promotions handled?
- Under what conditions can leave be refused?
- What are the rules for suspension and leave?
- Compare earned leave and other types of leave
- What are the key benefits provided after retirement?
- Explain the rules related to leave and pension together
- What is the maximum leave encashment allowed?
- How is earned leave calculated?
- Explain leave encashment rules

⚠️ Important Behavior
Answers are based ONLY on uploaded documents
No general knowledge
Irrelevant queries → The requested information is not available in the provided documents.

🏗️ Architecture
Frontend (HTML/CSS/JS)
        ↓
FastAPI Backend
        ↓
PDF → Text → Chunking
        ↓
Embeddings (Sentence Transformers)
        ↓
FAISS Vector Search
        ↓
Groq LLM
        ↓
Answer + Sources

⚙️ Configuration
Parameter	Value
Chunk Size	500
Overlap	        80
Top-K	        3–5
Threshold	~0.4
Model	        llama-3.1-8b-instant

🛡️ Reliability
✅ No hallucination
✅ Context-grounded answers
✅ Source verification
✅ Rejects irrelevant queries

🆓 Tech Stack
Layer	         Technology
Backend	         FastAPI
Embeddings	 sentence-transformers
Vector DB	 FAISS
PDF Parsing	 PyMuPDF
LLM	         Groq
Frontend	 HTML, CSS, JS

🎯 Use Case
Government employees
Policy researchers
Administrative systems
👉 Enables fast access to official rules.

📸 Screenshots
### 💬 Chat Interface
[Chat UI](assets/chat_ui.png)
### 📂 Upload Documents
[Upload](assets/upload_section.png)
### 📄 Answer with Sources
[Sources](assets/sources_view.png)

🚀 Future Improvements
Deployment on ML platforms (Hugging Face Spaces / Railway)
Model caching
Background indexing
Multi-language support
UI enhancements

👨‍💻 Author
Team **MINDMESH**

⭐ Final Note
This project demonstrates how RAG-based AI systems can deliver reliable, document-grounded answers for real-world governance use cases.
