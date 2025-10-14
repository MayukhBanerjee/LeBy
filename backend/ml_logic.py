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
from langchain_core.embeddings import Embeddings  # interface for FAISS


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

    def __init__(self, model: str = "models/text-embedding-004"):
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
def _pick_model() -> str:
    """
    Try several Gemini chat model IDs and pick the first working one.
    This eliminates 'model not found' errors across API regions.
    """
    candidates = ["gemini-2.0-flash"]
    for model_name in candidates:
        try:
            mdl = genai.GenerativeModel(model_name)
            r = mdl.generate_content("healthcheck")
            if hasattr(r, "text") or getattr(r, "candidates", None):
                print(f"[LLM] Using Gemini model: {model_name}")
                return model_name
        except Exception as e:
            print(f"[LLM] Probe failed for {model_name}: {e}")
            continue
    raise RuntimeError("❌ No compatible Gemini chat model found for this API key.")


CHAT_MODEL = _pick_model()


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

    def __init__(self, full_text: str, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.full_text = full_text
        self.vector_store_path = os.path.join(VECTOR_STORE_DIR, self.session_id)
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
            "You are an expert legal summarizer. "
            "Summarize the document concisely and professionally in markdown.\n\n"
            "Guidelines:\n"
            "- Length: under 250 words total.\n"
            "- Structure: Purpose, Key Parties, Key Clauses/Obligations, Important Dates, and Notable Points.\n"
            "- Use short phrases or single-sentence bullets.\n"
            "- Avoid repetition and filler words.\n"
            "- Use clear section headers with **bold** labels (no *asterisks*).\n\n"
            "Document text:\n"
            f"{self.full_text[:8000]}\n\n"
            "Now output the summary directly in markdown without preamble or closing lines."
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
        - If information is missing, give best-practice guidance first, then ask 2–3 clarifying questions.
        - Keep it concise and direct.
        """
        # Retrieve top chunks for grounding
        db = _load_faiss(self.vector_store_path)
        retriever = db.as_retriever(search_kwargs={"k": 6})
        docs = retriever.get_relevant_documents(query or "next steps action plan")
        context = "\n\n".join(d.page_content for d in docs)

        # Safety net: include a small slice of the full text to avoid “no context” answers
        safety_slice = self.full_text[:2000]

        # Light conversation memory
        history_block = ""
        if self.history:
            pairs = [f"User: {h['user']}\nAssistant: {h['assistant']}" for h in self.history[-5:]]
            history_block = "Recent conversation:\n" + "\n\n".join(pairs) + "\n\n"

        # Concise, structured prompt
        prompt = (
            "You are an intelligent, practical legal assistant.\n"
            "USE the provided document context to answer. If the question is broad "
            "(e.g., 'what should I do next?'), infer the most likely next steps from the context "
            "and provide a concrete action plan.\n\n"
            "STYLE & LENGTH CONSTRAINTS:\n"
            "- Total length: UNDER 150 words.\n"
            "- Be direct. No filler, no disclaimers.\n"
            "- Use **bold** section labels and short bullets starting with '* '.\n"
            "- If something is missing, infer from context and clearly state assumptions.\n\n"
            "RESPONSE FORMAT (strict):\n"
            "1) **Direct Answer / Next Steps** – 1–2 sentences max.\n"
            "2) **Action Plan** – 3–5 bullets (who to contact, deadlines, documents to gather).\n"
            "3) **Risks / Caveats** – up to 3 bullets (only if relevant).\n"
            "4) **Clarify** – up to 3 short questions ONLY if critical.\n\n"
            f"{history_block}"
            f"User question:\n{query}\n\n"
            "--- Retrieved context from the document ---\n"
            f"{context}\n"
            "-------------------------------------------\n\n"
            "--- Safety slice of full document (fallback) ---\n"
            f"{safety_slice}\n"
            "------------------------------------------------\n\n"
            "Now produce the response EXACTLY in the format above, within 150 words."
        )

        answer = self._generate(prompt)

        # Store history
        self.history.append({"user": query, "assistant": answer})
        if len(self.history) > 25:
            self.history = self.history[-25:]

        return answer
