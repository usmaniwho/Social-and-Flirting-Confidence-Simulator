import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Container, Box } from '@mui/material';
import axios from 'axios';
import Home from './components/Home';
import Calibration from './components/Calibration';
import SelectSession from './components/SelectSession';
import Session from './components/Session';
import Feedback from './components/Feedback';
import Navbar from './components/Navbar';

const theme = createTheme({
  palette: {
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
    },
  },
});

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [userId] = useState('user_' + Math.random().toString(36).substr(2, 9));

  useEffect(() => {
    // Set up axios defaults
    axios.defaults.baseURL = 'http://localhost:8000';
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ flexGrow: 1, minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <Navbar />
          <Container maxWidth="lg" sx={{ py: 4 }}>
            <Routes>
              <Route path="/" element={<Home userId={userId} setSessionId={setSessionId} />} />
              <Route path="/calibration" element={<Calibration userId={userId} />} />
              <Route path="/select-session" element={<SelectSession userId={userId} setSessionId={setSessionId} />} />
              <Route path="/session" element={<Session sessionId={sessionId} />} />
              <Route path="/feedback" element={<Feedback sessionId={sessionId} />} />
            </Routes>
          </Container>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
