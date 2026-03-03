# 🧠 LeBy – Intelligent Legal Assistant

LeBy is an AI-powered legal assistant that combines **Retrieval-Augmented Generation (RAG)**, semantic search, and structured response generation to provide document-grounded legal guidance and general legal help.

It supports:

- 📄 Legal document upload & analysis
- 🔍 Context-aware question answering
- 🧠 Retrieval-based reasoning (FAISS)
- 💬 General legal assistance (non-RAG mode)
- ✅ Structured, actionable legal outputs

---

# 🚀 Features

## 📄 Document Analysis Mode (RAG-Based)

- Upload PDF or paste legal text
- Automatic text extraction using PDF.js
- Intelligent text chunking
- Embedding generation
- FAISS vector database storage
- Semantic retrieval per query
- Context-grounded LLM responses
- Structured legal action plan outputs

---

## 💬 General Legal Help Mode (Agent-Based)

- No document required
- Direct LLM reasoning
- Practical next-step guidance
- Structured output (Actions, Risks, Clarifications)
- Fully isolated from vector database

---

# 🏗 System Architecture

```
Frontend (React + MUI)
        ↓
FastAPI Backend
        ↓
Mode Router
  ├── Document Mode → RAG Pipeline (FAISS)
  └── General Mode → Direct Agent (No Vector DB)
```

---

# 🧠 AI Components

- Gemini 2.x Chat Model
- FAISS Vector Database
- Retrieval-Augmented Generation
- Structured Prompt Engineering
- Adaptive Chunking Strategy

---

# 🛠 Tech Stack

## Frontend
- React
- Material UI
- Axios
- PDF.js

## Backend
- FastAPI
- Uvicorn
- FAISS
- Google Generative AI (Gemini)
- Python 3.10+

---

# 📦 Installation & Setup

---

## 1️⃣ Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/leby.git
cd leby
```

---

## 2️⃣ Backend Setup

```bash
cd backend
python -m venv venv
```

### Activate Virtual Environment

Windows:
```bash
venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Environment Variables

Create a `.env` file inside the backend directory:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

⚠️ Do NOT commit this file.

---

## 4️⃣ Run Backend Server

```bash
uvicorn main:app --reload --port 8000
```

Backend runs at:

```
http://localhost:8000
```

API Docs:

```
http://localhost:8000/docs
```

---

## 5️⃣ Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
```

Optional `.env` inside frontend:

```
REACT_APP_API_BASE_URL=http://localhost:8000
```

Run frontend:

```bash
npm start
```

Frontend runs at:

```
http://localhost:3000
```

---

# 🔍 How It Works

## 📄 Document Mode Flow

1. User uploads PDF or pastes text
2. Backend extracts and chunks text
3. Embeddings generated
4. Stored in FAISS vector DB
5. On user query:
   - Relevant chunks retrieved
   - Injected into prompt
   - Gemini generates structured response
6. Response returned to frontend

---

## 💬 General Mode Flow

1. No document uploaded
2. No embeddings created
3. No FAISS usage
4. Direct agent reasoning
5. Structured legal output

---

# 📁 Project Structure

```
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
│   ├── src/
│   │   ├── App.js
│   │   └── ...
│   ├── package.json
│   └── .env
│
└── README.md
```

---

# 🔐 Security & Design Decisions

- API keys stored in `.env`
- Session-based document isolation
- Vector DB not used in General Mode
- Safe HTML rendering
- Structured prompt constraints
- No automatic document persistence

---

# 📊 Example Use Cases

- FIR interpretation
- Rental agreement analysis
- Employment contract review
- Legal notice breakdown
- Consumer dispute planning
- Accident next-step guidance
- Police interaction advice

---

# 🧪 Testing Endpoints

| Endpoint | Purpose |
|----------|----------|
| `POST /session/start-from-text` | Create document session |
| `GET /session/status/{session_id}` | Check processing status |
| `POST /session/query` | Ask question (RAG mode) |
| `POST /general/query` | Ask question (Agent mode) |

---

# 📌 Design Philosophy

LeBy is built around:

- Clear separation of RAG and Agent modes
- Minimal hallucination through retrieval grounding
- Structured legal output formatting
- Practical, action-oriented responses
- Clean system isolation

---

# 🚀 Future Improvements

- Persistent vector storage
- User authentication
- Multi-document sessions
- Cloud deployment
- Case law database integration
- Legal citation grounding
- Fine-tuned domain models

---

# 👨‍💻 Author

**Mayukh Banerjee**

AI Engineer | RAG Systems | Applied LLM Architect

---

# ⭐ Why LeBy?

Most legal AI tools:

- Hallucinate
- Provide vague guidance
- Lack structured next steps

LeBy solves this by combining:

- Retrieval grounding
- Structured response format
- Practical action plans
- Clean architecture separation

---

If you found this project interesting, consider starring ⭐ the repository.