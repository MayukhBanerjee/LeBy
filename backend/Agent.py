import os
import time
import uuid
from typing import List, Dict
from dotenv import load_dotenv

# --- Gemini SDK (direct official API) ---
import google.generativeai as genai

# --- LangChain utilities we still use ---
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


# ---------------------------------------------------------------------
# 1. ENV + GOOGLE SDK SETUP
# ---------------------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in the .env file.")

genai.configure(api_key=API_KEY)
VECTOR_STORE_DIR = "vector_stores"
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# 2. EMBEDDINGS WRAPPER
# ---------------------------------------------------------------------
class GoogleSDKEmbeddings(Embeddings):
    """
    Lightweight wrapper using Gemini's official embeddings API.
    Avoids storing huge arrays; each chunk is embedded individually.
    """

    def __init__(self, model: str = "models/gemini-embedding-001"):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            try:
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document",
                )
                vectors.append(result["embedding"])
                time.sleep(0.05)  # small rate-limit cushion
            except Exception as e:
                print(f"[EMB] Skipped chunk due to error: {e}")
        return vectors

    def embed_query(self, text: str) -> List[float]:
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]


EMB = GoogleSDKEmbeddings()


# ---------------------------------------------------------------------
# 3. MODEL PICKER (ROBUST FALLBACK)
# ---------------------------------------------------------------------

CHAT_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------
# 4. HELPERS
# ---------------------------------------------------------------------
def _chunk_text(full_text: str) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_documents([Document(page_content=full_text)])


def _save_faiss(db: FAISS, path: str) -> None:
    db.save_local(path)


def _load_faiss(path: str) -> FAISS:
    return FAISS.load_local(path, EMB, allow_dangerous_deserialization=True)


# ---------------------------------------------------------------------
# 5. MAIN CLASS
# ---------------------------------------------------------------------
class DocumentSession:
    """
    Handles document ingestion, FAISS indexing, summary generation,
    and intelligent question answering using Gemini SDK.
    """

    def __init__(self, full_text: str, session_id: str | None = None, is_general: bool = False):
        self.session_id = session_id or str(uuid.uuid4())
        self.full_text = full_text
        self.is_general = is_general
        self.vector_store_path = os.path.join(VECTOR_STORE_DIR, self.session_id)
        if not self.is_general:
            self._prepare_vector_store()
        self.history: List[Dict[str, str]] = []

    # ------------------------------------------------------------
    # STEP 1: Create FAISS index (streaming, memory-safe)
    # ------------------------------------------------------------
    def _prepare_vector_store(self):
        docs = _chunk_text(self.full_text)
        print(f"[{self.session_id}] Split into {len(docs)} chunks.")
        db = None

        for i, doc in enumerate(docs, start=1):
            try:
                if db is None:
                    db = FAISS.from_texts([doc.page_content], EMB)
                else:
                    db.add_texts([doc.page_content])
                if i % 20 == 0 or i == len(docs):
                    print(f"[{self.session_id}] Processed {i}/{len(docs)} chunks.")
                time.sleep(0.1)
            except Exception as e:
                print(f"[{self.session_id}] Error embedding chunk {i}: {e}")
                continue

        _save_faiss(db, self.vector_store_path)
        print(f"[{self.session_id}] Vector store saved at {self.vector_store_path}.")

    # ------------------------------------------------------------
    # STEP 2: Core Gemini generation
    # ------------------------------------------------------------
    def _generate(self, prompt: str) -> str:
        model = genai.GenerativeModel(CHAT_MODEL)
        resp = model.generate_content(prompt)
        return getattr(resp, "text", "").strip() or "⚠️ No response generated."

    # ------------------------------------------------------------
    # STEP 3: Document summary
    # ------------------------------------------------------------
    def get_initial_summary(self) -> str:
        """
        Generate a concise executive summary for the uploaded or pasted document.
        Keep it short (≤ 250 words), factual, and well structured.
        """
        prompt = (
            "You are a Senior Legal Document Specialist.\n"
            "Generate a high-level executive summary of the provided text.\n\n"
            "REQUIREMENTS:\n"
            "- Tone: Formal, objective, and precise.\n"
            "- Format: Use professional markdown with semantic headers.\n"
            "- Sections: Executive Overview, Key Parties, Significant Obligations, Critical Deadlines, and Potential Red Flags.\n\n"
            "Document Text Segment:\n"
            f"{self.full_text[:12000]}\n\n"
            "Deliver the summary directly without any introductory conversational text."
        )
        
        return self._generate(prompt)

    # ------------------------------------------------------------
    # STEP 4: Query answering (context + memory)
    # ------------------------------------------------------------
    def answer_query(self, query: str) -> str:
        """
        Answer follow-up questions with strong, action-oriented guidance.
        - Always ground in retrieved context.
        - If the user asks something vague (“what should I do”), still propose next steps.
        - If information is missing, give best-practice guidance first, then ask 2 to 3 clarifying questions.
        - Keep it concise and direct.
        """
        # Retrieve top chunks for grounding
        if self.is_general:
            context = "General Legal Help - No specific document context provided. You are to act as a general legal assistant advising on common legal issues based on your instructions. Note: This is an ungrounded chat about the user's generic problem."
        else:
            db = _load_faiss(self.vector_store_path)
            retriever = db.as_retriever(search_kwargs={"k": 6})
            docs = retriever.get_relevant_documents(query or "next steps action plan")
            context = "\n\n".join(d.page_content for d in docs)

        # Safety net: include a small slice of the full text to avoid “no context” answers
        safety_slice = self.full_text[:2000] if not self.is_general else ""

        # Light conversation memory
        history_block = ""
        if self.history:
            pairs = [f"User: {h['user']}\nAssistant: {h['assistant']}" for h in self.history[-5:]]
            history_block = "Recent conversation:\n" + "\n\n".join(pairs) + "\n\n"

        # Determine context constraints based on mode
        if self.is_general:
            persona = (
                "You are an elite legal strategist. You are providing general guidance without a specific document.\n"
                "FOCUS: Practical first steps, risk mitigation, and identifying which specialist (e.g., criminal lawyer, employment tribunal) is needed."
            )
            context_guidance = (
                "Since no document is uploaded, provide high-level strategic advice based on general legal principles. "
                "Structure your response with clear, actionable bullet points."
            )
        else:
            persona = (
                "You are an elite legal analyst. Use the provided document as your sole source of truth."
            )
            context_guidance = (
                "Always ground your answer in the provided document context. If the document is silent, "
                "state so clearly and then provide best-practice guidance as a secondary measure."
            )

        # Concise, structured prompt
        prompt = (
            f"{persona}\n\n"
            f"{context_guidance}\n\n"
            "RESPONSE STYLE:\n"
            "- Tone: Authoritative, professional, but accessible.\n"
            "- Structure: Primary Answer -> Action Steps -> Strategic Considerations.\n"
            "- Conciseness: Maximum 200 words.\n\n"
            
            f"{history_block}"
            f"User Question: {query}\n\n"
        
            "--- Context / Strategic Instructions ---\n"
            f"{context}\n"
            "------------------------------------------\n\n"
        
            "Now deliver your final guidance in professional markdown."
        )
        

        answer = self._generate(prompt)

        # Store history
        self.history.append({"user": query, "assistant": answer})
        if len(self.history) > 25:
            self.history = self.history[-25:]

        return answer
