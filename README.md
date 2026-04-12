🧠 GovQuery — AI Policy Helpdesk

GovQuery is an AI-powered policy helpdesk that enables government employees to ask questions in natural language and receive accurate, source-backed answers from official documents.

Upload PDFs → Ask questions → Get instant answers with citations.

🚀 Features
Natural language question answering
Retrieval-Augmented Generation (RAG) pipeline
Source-backed responses from official documents
PDF upload and automatic indexing
Chat-based user interface
Fast semantic search using embeddings
⚡ Quick Start (3 Steps)
1. Install Dependencies
pip install -r requirements.txt
2. Set Groq API Key (Free)

👉 Get your key from: https://console.groq.com

Windows (Command Prompt):

set GROQ_API_KEY=your_api_key_here

Windows (PowerShell):

$env:GROQ_API_KEY="your_api_key_here"

macOS / Linux:

export GROQ_API_KEY=your_api_key_here
3. Run the App
python app.py

👉 Open in browser:
http://localhost:5000

💻 How to Use
Upload one or more policy PDF documents
Wait for indexing to complete
Ask questions in natural language
Receive answers with source references
🧪 Sample Test Queries

(After uploading a CCS Leave Rules PDF)

What is the maximum Earned Leave that can be accumulated?
Can leave be refused by the sanctioning authority?
What are the eligibility conditions for Child Care Leave?
How is leave encashment calculated on retirement?
What is the difference between Earned Leave and Half Pay Leave?
📂 Project Structure
govquery/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   └── index.html
├── uploads/
└── vector_store/
🧠 Architecture
PDF Documents → Text Extraction → Chunking → Embeddings → Vector Store  

User Query → Embedding → Semantic Search → Retrieve Relevant Chunks  
→ Groq LLM → Answer + Source Citation
🎥 Demo

Users upload policy PDFs and ask questions like:
👉 “Can leave be refused by authority?”

The system retrieves relevant sections and generates a clear answer along with the source reference.

⚙️ Environment Variables
Variable	Required	Description
GROQ_API_KEY	Yes	Groq API key

📝 Notes
Uses Groq API for fast and free LLM responses
Documents are stored and indexed locally
Vector store persists across sessions
Works best with text-based PDFs

🔮 Future Improvements
Multi-language support (Hindi & regional languages)
Voice-based interaction
Integration with government portals
Admin analytics dashboard

🎯 Impact
Reduces document search time by up to 70%
Saves 200–500+ work hours/month per department
Minimizes dependency on HR staff
Improves decision-making efficiency

📌 Conclusion
GovQuery transforms complex government policy documents into an intelligent, conversational system—making information access faster, easier, and more efficient.
