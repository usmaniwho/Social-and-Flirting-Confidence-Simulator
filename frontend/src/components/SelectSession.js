import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardContent, Typography, Button, Grid, Box,
  FormControl, InputLabel, Select, MenuItem, Alert
} from '@mui/material';
import axios from 'axios';

const SelectSession = ({ userId, setSessionId }) => {
  const [modes, setModes] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [personalities, setPersonalities] = useState([]);
  const [selectedMode, setSelectedMode] = useState('');
  const [selectedScenario, setSelectedScenario] = useState('');
  const [selectedPersonality, setSelectedPersonality] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchOptions();
  }, []);

  const fetchOptions = async () => {
    try {
      const [modesRes, personalitiesRes] = await Promise.all([
        axios.get('/session/modes'),
        axios.get('/session/personalities')
      ]);
      setModes(modesRes.data.modes);
      setPersonalities(personalitiesRes.data.personalities);
    } catch (err) {
      setError('Failed to load options');
    }
  };

  const fetchScenarios = async (mode) => {
    try {
      const res = await axios.get(`/session/scenarios/${mode}`);
      setScenarios(res.data.scenarios);
    } catch (err) {
      setError('Failed to load scenarios');
    }
  };

  const handleModeChange = (mode) => {
    setSelectedMode(mode);
    setSelectedScenario('');
    fetchScenarios(mode);
  };

  const startSession = async () => {
    if (!selectedMode || !selectedScenario || !selectedPersonality) {
      setError('Please select all options');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await axios.post('/session/start', {
        user_id: userId,
        mode: selectedMode,
        scenario: selectedScenario,
        personality: selectedPersonality
      });

      setSessionId(res.data.session_id);
      navigate('/session');
    } catch (err) {
      setError('Failed to start session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ textAlign: 'center', color: 'white' }}>
      <Typography variant="h3" component="h1" gutterBottom>
        Choose Your Practice Scenario
      </Typography>
      <Typography variant="h6" gutterBottom>
        Pick a situation that matches what you want to practice
      </Typography>

      <Grid container spacing={3} justifyContent="center" sx={{ mt: 4 }}>
        <Grid item xs={12} md={6}>
          <Card sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)'
          }}>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
                🎯 Session Configuration
              </Typography>

              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel sx={{ color: 'black' }}>Mode</InputLabel>
                <Select
                  value={selectedMode}
                  onChange={(e) => handleModeChange(e.target.value)}
                  label="Mode"
                  sx={{ color: 'black', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'black' } }}
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white'
                      }
                    }
                  }}
                >
                  {modes.map(mode => (
                    <MenuItem key={mode} value={mode} sx={{ color: 'white' }}>{mode.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth sx={{ mb: 2 }} disabled={!selectedMode}>
                <InputLabel sx={{ color: 'black' }}>Scenario</InputLabel>
                <Select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  label="Scenario"
                  sx={{
                    color: 'black',
                    '& .MuiOutlinedInput-notchedOutline': { borderColor: 'black' },
                    '& .MuiOutlinedInput-root.Mui-disabled': { opacity: 1 },
                    '& .MuiOutlinedInput-notchedOutline.Mui-disabled': { borderColor: 'black' }
                  }}
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white'
                      }
                    }
                  }}
                >
                  {scenarios.map(scenario => (
                    <MenuItem key={scenario} value={scenario} sx={{ color: 'white' }}>{scenario.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel sx={{ color: 'black' }}>AI Personality</InputLabel>
                <Select
                  value={selectedPersonality}
                  onChange={(e) => setSelectedPersonality(e.target.value)}
                  label="AI Personality"
                  sx={{ color: 'black', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'black' } }}
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white'
                      }
                    }
                  }}
                >
                  {personalities.map(personality => (
                    <MenuItem key={personality} value={personality} sx={{ color: 'white' }}>{personality.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                size="large"
                onClick={startSession}
                disabled={loading || !selectedMode || !selectedScenario || !selectedPersonality}
                sx={{ minWidth: 200 }}
              >
                {loading ? 'Starting...' : 'Start Session'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SelectSession;
