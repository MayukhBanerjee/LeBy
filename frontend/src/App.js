import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import * as pdfjsLib from "pdfjs-dist";
import {
  Container,
  Box,
  Typography,
  TextField,
  IconButton,
  Paper,
  CircularProgress,
  Snackbar,
  Alert,
  Button,
  LinearProgress,
  Card,
  CardContent,
  TextareaAutosize,
  Chip,
  Stack
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import ArticleIcon from "@mui/icons-material/Article";
import GavelIcon from "@mui/icons-material/Gavel";
import "./App.css";

// Configure PDF.js worker via CDN matching installed version
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

// --- API BASE URL ---
const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

// --- Helper: Extract text from PDF ---
async function extractPdfText(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  let text = "";
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    text += content.items.map((t) => t.str).join(" ") + "\n\n";
  }
  return text.trim();
}

// --- Markdown-ish to safe HTML (bold, bullets, newlines) ---
function formatAiTextToHtml(raw) {
  if (!raw) return "";
  let html = raw;

  // Normalize Windows newlines
  html = html.replace(/\r\n/g, "\n");

  // Convert markdown bold **text** to <strong>
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Convert list-style lines beginning with "* " into indented bullets
  // Handles lines that start with "* " or newline + "* "
  html = html.replace(/(^|\n)\*\s+(.*)/g, (_, p1, p2) => {
    return `${p1}&nbsp;&nbsp;&nbsp;&nbsp;• ${p2}`;
  });

  // Italics for single-asterisk wrapped words that are not list bullets
  html = html.replace(/\*(?!\s|\*)([^*\n]+)\*/g, "<em>$1</em>");

  // Convert remaining newlines to <br>
  html = html.replace(/\n/g, "<br/>");

  return html;
}

// --- Header Component ---
function Header({ onReset }) {
  return (
    <Box
      sx={{
        p: 2,
        borderBottom: "1px solid #e5e7eb",
        bgcolor: "primary.main",
        color: "white",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between"
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center">
        <GavelIcon />
        <Typography variant="h5" fontWeight="bold">
          LeBy – Intelligent Legal Assistant
        </Typography>
      </Stack>
      {onReset && (
        <Button
          variant="contained"
          color="secondary"
          onClick={onReset}
          sx={{ textTransform: "none" }}
        >
          New Session
        </Button>
      )}
    </Box>
  );
}

export default function App() {
  const [appState, setAppState] = useState("input"); // input | processing | chat
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [currentFile, setCurrentFile] = useState("");
  const [notification, setNotification] = useState({
    open: false,
    message: "",
    severity: "info"
  });

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const pollRef = useRef(null);

  // Scroll to bottom on message update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cleanup polling interval
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // --- Utility: Toast ---
  const showToast = (message, severity = "info") =>
    setNotification({ open: true, message, severity });

  // --- Poll backend until READY ---
  const pollStatus = (sid, filename) => {
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await axios.get(`${API_BASE_URL}/session/status/${sid}`);
        if (data.status === "READY") {
          clearInterval(pollRef.current);
          setMessages([
            {
              sender: "ai",
              text:
                `✅ Analysis of "${filename}" complete!\n\n` +
                `--- Summary ---\n${data.summary}\n\n` +
                `Now you can ask me questions like “What should I do next?”, “Who can help?”, or “Explain Section 4.”`
            }
          ]);
          setAppState("chat");
        } else if (data.status === "ERROR") {
          clearInterval(pollRef.current);
          showToast("Processing failed. Please try again.", "error");
          setAppState("input");
        }
      } catch {
        clearInterval(pollRef.current);
        showToast("Could not get session status.", "error");
        setAppState("input");
      }
    }, 2500);
  };

  // --- Start New Session from Text ---
  const startSession = async (text, filename) => {
    if (!text || text.trim().length < 100) {
      showToast("Please provide at least 100 characters of text.", "warning");
      return;
    }
    setAppState("processing");
    setCurrentFile(filename);
    try {
      const { data } = await axios.post(`${API_BASE_URL}/session/start-from-text`, {
        text,
        filename
      });
      setSessionId(data.session_id);
      pollStatus(data.session_id, data.filename);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ??
        "Failed to start session. Is the backend running?";
      showToast(msg, "error");
      setAppState("input");
    }
  };

  // --- Handle File Upload ---
  const onFileChosen = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await extractPdfText(file);
      await startSession(text, file.name);
    } catch {
      showToast("Could not extract text from PDF.", "error");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // --- Handle Chat Message Send ---
  const onSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    const question = inputValue.trim();
    setInputValue("");
    setMessages((m) => [...m, { sender: "user", text: question }]);
    setIsLoading(true);
    try {
      const { data } = await axios.post(`${API_BASE_URL}/session/query`, {
        session_id: sessionId,
        query: question
      });
      setMessages((m) => [...m, { sender: "ai", text: data.response }]);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ??
        "Sorry, something went wrong while processing your question.";
      setMessages((m) => [...m, { sender: "ai", text: msg }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Render: Input Screen ---
  const InputScreen = (
    <Box
      sx={{
        p: 4,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 3
      }}
    >
      <Typography variant="h6" color="text.secondary">
        Start by providing a document
      </Typography>
      <Box sx={{ display: "flex", gap: 3, width: "100%", flexWrap: "wrap" }}>
        {/* Upload PDF */}
        <Card sx={{ flex: 1, minWidth: 320, textAlign: "center" }}>
          <CardContent>
            <UploadFileIcon sx={{ fontSize: 48, color: "primary.main" }} />
            <Typography sx={{ mt: 1.5 }}>Upload a PDF File</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Text is extracted locally in your browser, then analyzed securely.
            </Typography>
            <Button variant="contained" component="label">
              Choose PDF
              <input
                hidden
                type="file"
                ref={fileInputRef}
                accept=".pdf"
                onChange={onFileChosen}
              />
            </Button>
          </CardContent>
        </Card>

        {/* Paste Text */}
        <Card sx={{ flex: 1, minWidth: 320 }}>
          <CardContent sx={{ display: "flex", flexDirection: "column" }}>
            <ArticleIcon
              sx={{ fontSize: 48, color: "primary.main", alignSelf: "center" }}
            />
            <Typography sx={{ mt: 1.5, textAlign: "center" }}>
              Paste Document Text
            </Typography>
            <TextareaAutosize
              minRows={8}
              placeholder="Paste your legal document text here..."
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              style={{
                width: "100%",
                marginTop: 16,
                flex: 1,
                resize: "none",
                border: "1px solid #cbd5e1",
                borderRadius: 8,
                padding: 12,
                background: "white"
              }}
            />
            <Button
              variant="contained"
              sx={{ mt: 2, alignSelf: "flex-end" }}
              onClick={() => startSession(pastedText, "Pasted Text")}
              disabled={!pastedText.trim()}
            >
              Analyze Text
            </Button>
          </CardContent>
        </Card>
      </Box>

      <Stack direction="row" spacing={1}>
        <Chip label="Summarizes first" color="primary" variant="outlined" />
        <Chip label="Then you can chat with it" color="primary" variant="outlined" />
      </Stack>
    </Box>
  );

  // --- Render: Processing Screen ---
  const ProcessingScreen = (
    <Box sx={{ p: 4, textAlign: "center" }}>
      <Typography variant="h6">Analyzing “{currentFile}”…</Typography>
      <Typography color="text.secondary" sx={{ my: 1.5 }}>
        This may take a moment for large documents.
      </Typography>
      <LinearProgress />
    </Box>
  );

  // --- Render: Chat Screen ---
  const ChatScreen = (
    <>
      <Box sx={{ p: 1.5, borderBottom: "1px solid #e5e7eb" }}>
        <Typography variant="body2" color="text.secondary">
          Session: <strong>{currentFile}</strong>
        </Typography>
      </Box>

      <Box className="chat-window">
        {messages.map((m, i) => (
          <Box
            key={i}
            className="chat-message"
            sx={{
              mb: 2,
              display: "flex",
              justifyContent: m.sender === "user" ? "flex-end" : "flex-start"
            }}
          >
            <Paper
              elevation={1}
              sx={{
                p: 1.5,
                borderRadius: 2,
                bgcolor: m.sender === "user" ? "primary.main" : "white",
                color: m.sender === "user" ? "white" : "black",
                maxWidth: "80%",
                fontSize: "0.96rem",
                lineHeight: 1.6,
                wordBreak: "break-word",
                whiteSpace: "normal"
              }}
            >
              {/* Render user text as plain text with line breaks; AI text as formatted HTML */}
              {m.sender === "ai" ? (
                <div
                  style={{ textAlign: "left", marginLeft: "4px" }}
                  dangerouslySetInnerHTML={{ __html: formatAiTextToHtml(m.text) }}
                />
              ) : (
                <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
              )}
            </Paper>
          </Box>
        ))}
        {isLoading && (
          <CircularProgress
            size={22}
            sx={{ display: "block", ml: "auto", mr: 2, mt: 1 }}
          />
        )}
        <div ref={chatEndRef} />
      </Box>

      <Box
        component="form"
        onSubmit={onSend}
        sx={{ p: 2, borderTop: "1px solid #e5e7eb", display: "flex", gap: 1 }}
      >
        <TextField
          fullWidth
          placeholder="Ask a question about the document..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={isLoading}
        />
        <IconButton
          type="submit"
          color="primary"
          disabled={isLoading || !inputValue.trim()}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </>
  );

  // --- Main Layout ---
  return (
    <Container maxWidth="lg" sx={{ my: 3, height: "94vh" }}>
      <Paper
        elevation={4}
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          borderRadius: 3,
          overflow: "hidden"
        }}
      >
        <Header
          onReset={
            appState === "chat"
              ? () => {
                  setAppState("input");
                  setSessionId(null);
                  setMessages([]);
                  setPastedText("");
                  setCurrentFile("");
                }
              : undefined
          }
        />

        {appState === "input" && InputScreen}
        {appState === "processing" && ProcessingScreen}
        {appState === "chat" && ChatScreen}
      </Paper>

      <Snackbar
        open={notification.open}
        autoHideDuration={5000}
        onClose={() => setNotification((n) => ({ ...n, open: false }))}
      >
        <Alert
          onClose={() => setNotification((n) => ({ ...n, open: false }))}
          severity={notification.severity}
          sx={{ width: "100%" }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}
