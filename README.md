# ⚡ GovConnect — AI Policy Helpdesk

A **full-stack AI-powered policy assistant** that enables government employees to query official documents using **semantic search + LLM intelligence**.

🧠 No keyword matching. Only context-aware answers.

## ✨ Key Features

- 🔍 **Semantic Search (FAISS)** — understands meaning, not keywords  
- 🤖 **AI-Powered Answers (Groq LLM)** — accurate & context-based  
- 📄 **PDF Document Support** — upload multiple policy files  
- 🔗 **Source Transparency** — shows exact document references  
- 🎯 **Hallucination Control** — answers only from documents  
- ⚡ **Fast & Lightweight** — fully local embeddings + free API  

## 🖥️ Demo Preview

Chat interface similar to ChatGPT with document-backed answers.
- User asks a question  
- System retrieves relevant content  
- AI generates concise answer  
- Sources displayed for verification  

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
│ ├── chat_ui.png # Chat interface screenshot
│ ├── upload_section.png # Upload UI screenshot
│ └── sources_view.png # Source view screenshot
├── requirements.txt
└── README.md

## 🚀 Quick Start
1️⃣ Install Dependencies
bash
pip install -r requirements.txt
⚠️ First run downloads embedding model (~90MB)

2️⃣ Get Free Groq API Key
👉 https://console.groq.com
Sign up
Generate API key (gsk_...)

3️⃣ Run Backend
cd backend
uvicorn main:app --reload --port 8000
📍 Backend: http://localhost:8000
📍 Docs: http://localhost:8000/docs

4️⃣ Run Frontend
Open:
frontend/index.html

🧪 Example Queries
Question	Expected Result
What is lien?	Definition from Fundamental Rules
What is earned leave?	Leave rules explanation
Can leave be refused?	Rule-based answer
Steps for surplus staff redeployment	Process explanation
What is pension age?	❌ Not available (correct behavior)--> if related information is not found in uploaded documents!

🏗️ Architecture
Frontend (HTML/CSS/JS)
        ↓
FastAPI Backend
        ↓
PDF → Text → Chunking
        ↓
Sentence Transformers (Embeddings)
        ↓
FAISS Vector Search
        ↓
Groq LLM (Context-based Answer)
        ↓
Response + Source

⚙️ Configuration
Parameter	Value
Chunk Size	500 words
Overlap	80 words
Top-K	3–5
Similarity Threshold	~0.4
Model	llama-3.1-8b-instant

🛡️ Reliability & Accuracy
✅ No hallucination (strict prompt)
✅ Context-based answers only
✅ Rejects irrelevant queries
✅ Shows source for verification

🆓 Tech Stack
Layer	           Technology
Backend	        FastAPI
Embeddings	sentence-transformers
Vector DB	FAISS
PDF Parsing	PyMuPDF
LLM	        Groq (LLaMA 3.1)
Frontend	HTML, CSS, JavaScript

🎯 Use Case
Designed for:
Government employees
Policy researchers
Administrative systems

👉 Enables fast and accurate access to official rules and documents.

📸 Screenshots
### 💬 Chat Interface
[Chat UI](assets/chat_ui.png)
### 📂 Upload Documents
[Upload](assets/upload_section.png)
### 📄 Answer with Sources
[Sources](assets/sources_view.png)

## 🌐 Live Deployment

- Frontend (Vercel): https://govconnect-helpdesk-chatbot.vercel.app/ 
- Backend (Render): https://govconnect-backend-5jf3.onrender.com
⚠️ Note:
> The backend is deployed on Render (free tier), which may go into a sleep state after inactivity.
> As a result, the first request can take 30–60 seconds due to cold start.
> For demonstration purposes, the application can also be run locally for faster performance.

## 📂 Demo Instructions

To test the application correctly, please follow these steps:
### 1. Upload Sample Documents
Navigate to the sample_documents/ folder in this repository.

Upload all the provided PDF files into the application and click **"Index Documents"**.

### 2. Ask Relevant Questions
Once indexing is complete, use the following sample queries:

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

### ⚠️ Important Note
This system is designed to answer questions **only from the uploaded documents** using semantic search.
- Queries must be related to the uploaded PDFs  
- Irrelevant or unrelated questions will return:  
  "The requested information is not available in the provided documents."

### 💡 Tip for Best Experience
- Upload all sample documents before asking questions  
- Wait for indexing to complete  
- Use the sample queries provided above  

🚀 Future Improvements
🔍 Highlight matched text in UI
📊 Confidence score visualization
🧠 Multi-language support

👨‍💻 Author
Team **MINDMESH**

⭐ Final Note
This project demonstrates how AI can make governance more accessible, efficient, and intelligent.
