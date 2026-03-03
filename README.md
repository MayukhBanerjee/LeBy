🧠 LeBy – Intelligent Legal Assistant
An AI-powered legal assistant that combines Retrieval-Augmented Generation (RAG), semantic search, and structured response generation to provide document-grounded legal guidance and general legal help.

LeBy allows users to:

Upload legal documents (PDF or text)

Generate structured summaries

Ask contextual follow-up questions

Receive practical next-step legal guidance

Use general legal chat without document context

🚀 Features
📄 Document Analysis Mode (RAG-Based)
Upload PDF or paste legal text

Automatic text extraction using pdfjs

Semantic chunking + embeddings

FAISS vector database for retrieval

Context-grounded LLM responses

Structured legal action plans

Risk & caveat identification

💬 General Legal Help Mode (Non-RAG Agent)
No document required

Direct AI-powered legal reasoning

Structured practical guidance

Incident-based action planning

Clear next steps and documentation checklist

🏗 Architecture Overview
Frontend (React + MUI)
        ↓
FastAPI Backend
        ↓
Mode Router
  ├── Document Mode → RAG Pipeline (FAISS)
  └── General Mode → Direct Agent
🔍 RAG Pipeline (Document Mode)
User uploads document

Backend extracts & chunks text

Embeddings generated

Stored in FAISS vector DB

On query:

Semantic retrieval

Context injection

Gemini LLM response

Structured legal output

🤖 AI Components Used
Gemini 2.x (Chat Model)

FAISS (Vector Store)

Custom Prompt Engineering

Adaptive Retrieval Chunking

Structured Output Formatting

🛠 Tech Stack
Frontend
React

Material UI

Axios

PDF.js

Backend
FastAPI

Uvicorn

FAISS

Google Generative AI (Gemini)

Python 3.10+

📦 Installation & Setup
1️⃣ Clone Repository
git clone https://github.com/YOUR_USERNAME/leby.git
cd leby
2️⃣ Backend Setup
cd backend
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
Install dependencies:

pip install -r requirements.txt
3️⃣ Environment Variables
Create a .env file inside backend:

GOOGLE_API_KEY=your_gemini_api_key_here
⚠ Do NOT commit this file.

4️⃣ Run Backend
uvicorn main:app --reload --port 8000
Server will start at:

http://localhost:8000
5️⃣ Frontend Setup
Open new terminal:

cd frontend
npm install
If needed, create .env:

REACT_APP_API_BASE_URL=http://localhost:8000
Run frontend:

npm start
Frontend runs at:

http://localhost:3000
🧠 How It Works Internally
Document Mode
Creates a session

Stores document embeddings in FAISS

All queries routed through /session/query

Retrieval + LLM synthesis

Structured response formatting

General Mode
No session creation

No vector database usage

Queries routed to /general/query

Direct agent reasoning

Clean separation from RAG

🔐 Security & Best Practices
API keys stored in .env

No vector persistence in General Mode

Session-isolated document embeddings

Safe HTML rendering with sanitization

Strict prompt formatting constraints

📊 Example Use Cases
FIR interpretation

Rental agreement explanation

Employment contract analysis

Consumer complaint strategy

Police interaction guidance

Legal notice breakdown

Accident next-step planning

🧪 Testing
Backend health check:

GET /docs
Test endpoints:

POST /session/start-from-text

GET /session/status/{session_id}

POST /session/query

POST /general/query

📁 Project Structure
leby/
│
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── ml_logic.py
│   ├── vector_store.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/App.js
│   ├── package.json
│   └── ...
│
└── README.md
📌 Design Philosophy
LeBy is built around:

Clear mode isolation (RAG vs Agent)

Structured legal output

Actionable next steps

Practical over verbose

Minimal hallucination via retrieval grounding

🌍 Future Improvements
Persistent vector storage

User authentication

Multi-document sessions

Deployment (Render / Railway / AWS)

Case law database integration

Legal citation grounding

Role-based legal personas

👨‍💻 Author
Mayukh Banerjee

AI Engineer | RAG Systems | Applied LLM Architect

⭐ Why This Project Matters
Legal AI tools often:

Hallucinate

Give vague advice

Lack structured action steps

LeBy solves this by combining:

Retrieval grounding

Structured response format

Practical action-oriented outputs

Clean separation of RAG & general reasoning