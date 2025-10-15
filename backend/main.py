import os
import uuid
import traceback
from typing import Optional, Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml_logic import DocumentSession

# -------------------------------------------------
# App init
# -------------------------------------------------
app = FastAPI(
    title="LeBy Intelligent Text Processor API",
    version="4.0.0",
    description="Text-first API for legal document analysis: summarize + chat (RAG).",
)

# CORS
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session registry (ok for dev/demo)
sessions: Dict[str, Dict[str, Any]] = {}


# -------------------------------------------------
# Models
# -------------------------------------------------
class StartFromTextRequest(BaseModel):
    text: str = Field(..., min_length=100, description="Raw text to analyze")
    filename: str = Field(..., description="Display name for the source")


class StartSessionResponse(BaseModel):
    session_id: str
    filename: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    filename: str
    summary: Optional[str] = None


class QueryRequest(BaseModel):
    session_id: str
    query: str


class AgentResponse(BaseModel):
    response: str


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _process_text_background(text: str, session_id: str, filename: str) -> None:
    """Build vector store + initial summary, then mark session READY."""
    print(f"[{session_id}] Background processing started for {filename}")
    try:
        doc_session = DocumentSession(full_text=text, session_id=session_id)
        summary = doc_session.get_initial_summary()

        sessions[session_id].update(
            {
                "session_object": doc_session,
                "summary": summary,
                "status": "READY",
            }
        )
        print(f"[{session_id}] Processing complete. Session READY.")
    except Exception:
        traceback.print_exc()
        # mark session as error but keep filename
        sessions[session_id]["status"] = "ERROR"


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/session/start-from-text", response_model=StartSessionResponse)
async def start_session_from_text(
    request: StartFromTextRequest, background_tasks: BackgroundTasks
):
    # create session skeleton
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "status": "PROCESSING",
        "filename": request.filename,
        "summary": None,
        "session_object": None,
    }

    # do heavy lifting off-thread
    background_tasks.add_task(
        _process_text_background, request.text, session_id, request.filename
    )
    return {"session_id": session_id, "filename": request.filename}


@app.get("/session/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "status": session["status"],
        "filename": session["filename"],
        "summary": session.get("summary"),
    }


@app.post("/session/query", response_model=AgentResponse)
async def query_session(request: QueryRequest):
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.get("status") != "READY" or not session.get("session_object"):
        raise HTTPException(status_code=400, detail="Session not ready.")

    try:
        doc_session: DocumentSession = session["session_object"]
        answer = doc_session.answer_query(request.query)
        return {"response": answer}
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Agent encountered an error.")


# Add this at the very end of backend/main.py
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)