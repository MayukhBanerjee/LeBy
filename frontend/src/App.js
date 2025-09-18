// frontend/src/App.js

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import {
  Container, Box, Typography, TextField, IconButton, Paper,
  CircularProgress, Snackbar, Alert, Button
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import './App.css'; // We'll use this for custom scrollbars

function App() {
  // State management
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  
  // Ref for the hidden file input and scrolling the chat window
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // API endpoint
  const API_BASE_URL = 'http://localhost:8000';

  // Automatically scroll to the latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initial greeting message
  useEffect(() => {
    setMessages([{ 
      sender: 'ai', 
      text: 'Welcome to LeBy! Please upload a PDF document to begin.' 
    }]);
  }, []);

  // --- Event Handlers ---

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsLoading(true);
    setUploadedFileName('');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload-pdf/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setUploadedFileName(file.name);

      // Create a new AI message with the summary from the backend
      const summaryMessage = { 
        sender: 'ai', 
        text: `Document processed successfully. Here is a summary:\n\n${response.data.summary}` 
      };
      setMessages(prev => [...prev, summaryMessage]); // Add summary to chat

      setNotification({ open: true, message: "Document ready for Q&A.", severity: 'success' });

    } catch (error) {
      const errorMessage = error.response?.data?.detail || "An error occurred during file upload.";
      setNotification({ open: true, message: errorMessage, severity: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!inputValue.trim()) return;

    // Add user's message to the chat
    const userMessage = { sender: 'user', text: inputValue };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Send message to the agent endpoint
      const response = await axios.post(`${API_BASE_URL}/agent-query/`, { text: inputValue });
      const aiMessage = { sender: 'ai', text: response.data.response };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || "Sorry, something went wrong.";
      const aiErrorMessage = { sender: 'ai', text: errorMessage };
      setMessages(prev => [...prev, aiErrorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNotificationClose = (event, reason) => {
    if (reason === 'clickaway') return;
    setNotification({ ...notification, open: false });
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper elevation={3} sx={{ height: 'calc(90vh)', display: 'flex', flexDirection: 'column', borderRadius: '15px' }}>
        
        {/* Header */}
        <Box sx={{ p: 2, borderBottom: '1px solid #ddd', textAlign: 'center' }}>
          <Typography variant="h5" component="h1" fontWeight="bold" color="primary">
            LeBy - Legal AI Assistant ⚖️
          </Typography>
        </Box>

        {/* File Upload Section */}
        <Box sx={{ p: 2, borderBottom: '1px solid #ddd', display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadFileIcon />}
            onClick={() => fileInputRef.current.click()}
            disabled={isLoading}
          >
            Upload PDF
            <input type="file" ref={fileInputRef} hidden onChange={handleFileChange} accept=".pdf" />
          </Button>
          {uploadedFileName && <Typography variant="body2" color="text.secondary">Ready: {uploadedFileName}</Typography>}
        </Box>

        {/* Chat Messages */}
        <Box className="chat-window" sx={{ flexGrow: 1, p: 2, overflowY: 'auto', bgcolor: '#f7f9fc' }}>
          {messages.map((msg, index) => (
            <Box key={index} sx={{
              display: 'flex',
              justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              mb: 2,
            }}>
              <Paper
                elevation={1}
                sx={{
                  p: 1.5,
                  borderRadius: '10px',
                  bgcolor: msg.sender === 'user' ? '#1976d2' : '#ffffff',
                  color: msg.sender === 'user' ? '#ffffff' : '#000000',
                  maxWidth: '70%',
                  whiteSpace: 'pre-wrap'
                }}
              >
                {msg.text}
              </Paper>
            </Box>
          ))}
          <div ref={chatEndRef} />
        </Box>
        
        {isLoading && <CircularProgress sx={{ display: 'block', margin: '10px auto' }} />}

        {/* Message Input */}
        <Box component="form" onSubmit={handleSendMessage} sx={{ p: 2, borderTop: '1px solid #ddd', display: 'flex', alignItems: 'center' }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Ask a question about the document or give a command..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isLoading}
            sx={{ mr: 1 }}
          />
          <IconButton type="submit" color="primary" disabled={isLoading}>
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>

      {/* Notification Snackbar */}
      <Snackbar open={notification.open} autoHideDuration={6000} onClose={handleNotificationClose}>
        <Alert onClose={handleNotificationClose} severity={notification.severity} sx={{ width: '100%' }}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default App;