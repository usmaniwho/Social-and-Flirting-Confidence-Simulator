import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardContent, Typography, Button, Box, Grid,
  TextField, Alert, Chip
} from '@mui/material';
import axios from 'axios';

const Session = ({ sessionId }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState('');
  const [frsData, setFrsData] = useState(null);
  const [pendingAssistant, setPendingAssistant] = useState('');
  const lastAssistantRef = useRef('');

  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const frsWsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const navigate = useNavigate();

  // 🔹 Helper: Convert base64 to ArrayBuffer for audio playback
  const base64ToArrayBuffer = (base64) => {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  };

  // 🔹 Play received audio chunks
  const playAudioChunk = useCallback((audioChunk) => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const arrayBuffer = base64ToArrayBuffer(audioChunk);
    audioContext.decodeAudioData(arrayBuffer, (buffer) => {
      const source = audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(audioContext.destination);
      source.start();
    });
  }, []);

  // 🔹 WebSocket setup (voice + FRS)
  const connectWebSockets = useCallback(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/realtime/voice-stream`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Voice WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      // Add transcribed user text to chat as user message
      if (msg.user_text) {
        setMessages(prev => [...prev, { role: "user", content: msg.user_text }]);
      }

      // Handle assistant partials without spamming the message list
      if (msg.partial_text) {
        setPendingAssistant(msg.partial_text);
      }

      // Final assistant reply: append once and clear pending; dedupe identical replies
      if (msg.reply_text) {
        if (lastAssistantRef.current !== msg.reply_text) {
          setMessages(prev => [...prev, { role: "assistant", content: msg.reply_text }]);
          lastAssistantRef.current = msg.reply_text;
        }
        setPendingAssistant('');
      }

      if (msg.audio_chunk) {
        const audioData = Uint8Array.from(atob(msg.audio_chunk), c => c.charCodeAt(0));
        const blob = new Blob([audioData], { type: "audio/mpeg" });
        const audioURL = URL.createObjectURL(blob);
        const audio = new Audio(audioURL);
        audio.play().catch((err) => console.warn("Audio play error:", err));
      }

      if (msg.error) {
        console.error("Server error:", msg.error);
      }
    };

    ws.onclose = () => {
      console.log('Voice WebSocket closed');
      setIsConnected(false);
    };

    ws.onerror = (err) => console.error('WebSocket error:', err);

    // FRS websocket
    const frsWs = new WebSocket(`ws://localhost:8000/api/stream/${sessionId}`);
    frsWsRef.current = frsWs;

    frsWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.frs) setFrsData(data.frs);
    };
  }, [sessionId, playAudioChunk]);

  // 🔹 Fetch conversation history
  const fetchConversationHistory = useCallback(async () => {
    try {
      const res = await axios.get(`/api/conversation/history/${sessionId}`);
      setMessages(res.data.messages);
    } catch (err) {
      console.error('Failed to fetch conversation history');
    }
  }, [sessionId]);

  // 🔹 Start mic streaming
  const startVoiceStreaming = async () => {
    if (!isConnected) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      let recorder;
      try {
        recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      } catch (e1) {
        try {
          recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        } catch (e2) {
          recorder = new MediaRecorder(stream); // fallback to browser default
        }
      }
      mediaRecorderRef.current = recorder;

      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          const arrayBuffer = await event.data.arrayBuffer();
          const base64Audio = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

          wsRef.current.send(JSON.stringify({
            session_id: sessionId,
            audio: base64Audio
          }));
        }
      };

      mediaRecorderRef.current.start(3000); // send audio every 3s for more reliable decoding
      setIsRecording(true);
      console.log('🎤 Voice streaming started');
    } catch (err) {
      setError('Failed to start microphone streaming');
    }
  };

  // 🔹 Stop mic streaming
  const stopVoiceStreaming = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      mediaRecorderRef.current = null;
    }
    setIsRecording(false);
    console.log('🛑 Voice streaming stopped');
  };

  // 🔹 Toggle call on/off
  const toggleVoiceCall = () => {
    if (isRecording) stopVoiceStreaming();
    else startVoiceStreaming();
  };

  // 🔹 Send typed message
  const sendMessage = () => {
    if (!inputMessage.trim()) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'text',
        session_id: sessionId,
        message: inputMessage
      }));
      setMessages(prev => [...prev, { role: 'user', content: inputMessage }]);
      setInputMessage('');
    } else {
      setError('Connection not established');
    }
  };

  // 🔹 End session safely
  const endSession = async () => {
    try {
      // Inform backend to finalize FRS and summary
      await axios.post(`/api/session/end/${sessionId}`);

      if (wsRef.current) wsRef.current.close();
      if (frsWsRef.current) frsWsRef.current.close();
      stopVoiceStreaming();
      navigate(`/feedback`);
    } catch (err) {
      console.error('Failed to end session:', err);
      // Fallback: still navigate to feedback to avoid trapping the user
      navigate(`/feedback`);
    }
  };

  // 🔹 Camera setup
  const startVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      videoRef.current.srcObject = stream;
    } catch {
      setError('Failed to access camera');
    }
  };

  // 🔹 Initialize everything
  useEffect(() => {
    if (!sessionId) {
      navigate('/');
      return;
    }

    startVideo();
    connectWebSockets();
    fetchConversationHistory();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (frsWsRef.current) frsWsRef.current.close();
      stopVoiceStreaming();
    };
  }, [sessionId, navigate, connectWebSockets, fetchConversationHistory]);

  // 🔹 UI
  return (
    <Box sx={{ color: 'white' }}>
      <Typography variant="h4" gutterBottom align="center">
        Conversation Session
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '70vh', borderRadius: '16px' }}>
            <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2 }}>
                {messages.map((msg, index) => (
                  <Box key={index} sx={{ mb: 1, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                    <Chip
                      label={`${msg.role}: ${msg.content}`}
                      sx={{
                        backgroundColor: msg.role === 'user' ? 'rgba(255,255,255,0.8)' : 'rgba(255,215,0,0.8)',
                        color: '#333'
                      }}
                    />
                  </Box>
                ))}
                {pendingAssistant && (
                  <Box sx={{ mb: 1, textAlign: 'left', opacity: 0.8 }}>
                    <Chip
                      label={`assistant: ${pendingAssistant}`}
                      sx={{ backgroundColor: 'rgba(255,215,0,0.6)', color: '#333' }}
                    />
                  </Box>
                )}
              </Box>

              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  placeholder="Type your message..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                />
                <Button variant="contained" onClick={sendMessage}>Send</Button>
              </Box>

              <Box sx={{ mt: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
                <Button
                  variant={isRecording ? "outlined" : "contained"}
                  color={isRecording ? "error" : "primary"}
                  onClick={toggleVoiceCall}
                  disabled={!isConnected}
                >
                  {isRecording ? 'End Voice Call' : 'Start Voice Call'}
                </Button>

                <Button variant="contained" color="secondary" onClick={endSession}>
                  End Session
                </Button>


              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">📹 Live Video Feed</Typography>
              <video ref={videoRef} autoPlay muted style={{ width: '100%', borderRadius: '8px' }} />
            </CardContent>
          </Card>

          {frsData && (
            <Card>
              <CardContent>
                <Typography variant="h6">📊 Real-time FRS</Typography>
                <Typography>💫 Charisma: {frsData.charisma_friendliness?.toFixed(2)}</Typography>
                <Typography>🛡️ Confidence: {frsData.confidence_selfregulation?.toFixed(2)}</Typography>
                <Typography>❤️ Empathy: {frsData.emotional_attunement_empathy?.toFixed(2)}</Typography>
                <Typography>👂 Listening: {frsData.listening_reciprocal?.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default Session;
