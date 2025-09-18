# main.py

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the new processing function and the agent setup
import ml_logic

# --- App Initialization & CORS Configuration ---
app = FastAPI(
    title="LeBy - Legal AI Assistant API",
    version="1.0.0"
)

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    text: str

class AgentResponse(BaseModel):
    response: str

class UploadSuccessResponse(BaseModel):
    filename: str
    summary: str

# --- Initialize Agent ---
agent = ml_logic.setup_agent()

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the LeBy Legal AI Assistant API!"}

# In main.py

@app.post("/upload-pdf/", response_model=UploadSuccessResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Handles PDF uploads. It processes the document, generates an initial summary,
    and prepares the backend for Q&A. The summary is returned to the frontend.
    """
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)

    # CHANGE: Re-added the try...finally block to ensure cleanup
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        initial_summary = ml_logic.process_uploaded_pdf(file_path)

        return {"filename": file.filename, "summary": initial_summary}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    
"""  finally:
        #This block will now run and delete the file after the request is complete
        if os.path.exists(file_path):
            os.remove(file_path) """
            

@app.post("/agent-query/", response_model=AgentResponse)
async def agent_query(query: QueryRequest):
    """Handles user queries by passing them to the AI agent."""
    if not query.text:
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")
    
    try:
        agent_response = agent.run(query.text)
        return {"response": agent_response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed to process the query: {e}")