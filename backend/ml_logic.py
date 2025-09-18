# ml_logic.py

import os
import json
from dotenv import load_dotenv

# LangChain and Google AI imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.agents import Tool, initialize_agent, AgentType

# --- 1. SETUP & INITIALIZATION ---

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

# Initialize the Gemini models through LangChain
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Global variables to hold the context of the uploaded document
qa_chain_instance = None
full_document_text = ""


# --- 2. CORE AI FUNCTIONS ---

def get_gemini_summary(text: str) -> str:
    """Generates a summary for the given text using the Gemini API."""
    prompt = f"""
    You are an expert legal summarizer. Provide a concise, clear summary of the following legal text,
    focusing on the key arguments, decisions, and legal principles.

    Legal Text:
    ---
    {text[:8000]} 
    ---
    Concise Summary:
    """
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"An error occurred during summarization: {e}"

# --- 3. RAG & DOCUMENT PROCESSING ---

def process_uploaded_pdf(pdf_path: str):
    """
    Loads a PDF, creates a vector store for Q&A, extracts the full text,
    and generates an initial summary.
    """
    global qa_chain_instance, full_document_text
    
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # Store the full text for summarization or other general purpose tasks
    full_document_text = " ".join([doc.page_content for doc in documents])
    
    # Create vector store for RAG
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_documents(documents)
    db = FAISS.from_documents(docs, embeddings)
    
    # Create and store the Q&A chain instance globally
    qa_llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    qa_chain_instance = RetrievalQA.from_chain_type(
        llm=qa_llm,
        chain_type="stuff",
        retriever=db.as_retriever()
    )
    
    # Generate the initial summary after processing
    initial_summary = get_gemini_summary(full_document_text)
    
    return initial_summary

# --- 4. AGENTIC AI LAYER ---

# In ml_logic.py

# In ml_logic.py

def setup_agent():
    """Sets up the LangChain agent with its tools."""
    tools = [
        Tool(
            name="Document Q&A",
            func=lambda query: qa_chain_instance.invoke(query) if qa_chain_instance else "Error: No document has been uploaded for Q&A.",
            # CHANGE: Made this description very specific to guide the agent away from general queries.
            description="Use this tool ONLY for specific questions about the document's contents, like 'What is the date on page 3?' or 'Who is the landlord?'. Do NOT use it for general requests for explanation or summaries."
        ),
        Tool(
            name="General Summarizer and Explainer",
            func=lambda query: get_gemini_summary(full_document_text),
            # CHANGE: Made this the primary tool for any vague or general request.
            description="This is the primary tool to use for general, open-ended questions about the document in memory, such as 'explain this', 'what is this about?', or 'what should I do with this?'. It provides a comprehensive summary."
        )
    ]
    
    # Initialize the agent
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_iterations=10,
        handle_parsing_errors=True
    )
    return agent