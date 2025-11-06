import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardContent, Typography, Button, Box, Grid, Chip,
  Alert, List, ListItem, ListItemText
} from '@mui/material';
import axios from 'axios';

const Feedback = ({ sessionId }) => {
  const [feedbackData, setFeedbackData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const fetchFeedback = useCallback(async () => {
    try {
      const res = await axios.get(`/feedback/${sessionId}`);
      setFeedbackData(res.data);
    } catch (err) {
      setError('Failed to load feedback');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      navigate('/');
      return;
    }

    fetchFeedback();
  }, [sessionId, navigate, fetchFeedback]);

  const startNewSession = () => {
    navigate('/');
  };

  if (loading) {
    return <Typography>Loading feedback...</Typography>;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!feedbackData) {
    return <Typography>No feedback available</Typography>;
  }

  const { final_frs, feedback, objectives_completed, transcript, stars_earned } = feedbackData;

  return (
    <Box sx={{ color: 'white' }}>
      <Typography variant="h4" gutterBottom align="center">
        Great Job! Here's How You Did
      </Typography>

      <Grid container spacing={3} justifyContent="center">
        <Grid item xs={12} md={6} sx={{ display: 'flex' }}>
          <Card sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            flex: 1,
            display: 'flex',
            flexDirection: 'column'
          }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
                🎯 Final FRS Score
              </Typography>
              <Typography variant="h2" sx={{
                color: '#FFD700',
                fontWeight: 'bold',
                textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
                mb: 2
              }}>
                {final_frs ? final_frs.frs_score.toFixed(1) : 'N/A'}
              </Typography>

              <Box sx={{ mt: 3, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', p: 2 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>📊 Breakdown:</Typography>
                <Typography sx={{ mb: 1 }}>💫 Charisma & Friendliness: {final_frs ? final_frs.charisma_friendliness.toFixed(2) : 'N/A'}</Typography>
                <Typography sx={{ mb: 1 }}>🛡️ Confidence & Self-Regulation: {final_frs ? final_frs.confidence_selfregulation.toFixed(2) : 'N/A'}</Typography>
                <Typography sx={{ mb: 1 }}>❤️ Emotional Attunement & Empathy: {final_frs ? final_frs.emotional_attunement_empathy.toFixed(2) : 'N/A'}</Typography>
                <Typography sx={{ mb: 1 }}>👂 Listening & Reciprocal Communication: {final_frs ? final_frs.listening_reciprocal.toFixed(2) : 'N/A'}</Typography>
              </Box>

              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>🏆 Medals Earned:</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 1, mt: 1 }}>
                  {final_frs && final_frs.medals ? final_frs.medals.map((medal, index) => (
                    <Chip key={index} label={`🏅 ${medal}`} sx={{
                      backgroundColor: 'rgba(255,215,0,0.8)',
                      color: '#333',
                      fontWeight: 'bold',
                      '&:hover': { backgroundColor: 'rgba(255,215,0,1)' }
                    }} />
                  )) : <Typography sx={{ fontStyle: 'italic' }}>No medals earned yet</Typography>}
                </Box>
              </Box>

              <Box sx={{ mt: 3, backgroundColor: 'rgba(255,215,0,0.2)', borderRadius: '12px', p: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#FFD700' }}>
                  ⭐ Stars Earned: {stars_earned || 0}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} sx={{ display: 'flex', flexDirection: 'row', gap: 3 }}>
          <Card sx={{
            background: 'linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%)',
            color: 'white',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            flex: 1,
            display: 'flex',
            flexDirection: 'column'
          }}>
            <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
                💬 Overall Feedback
              </Typography>
              <Typography variant="body1" sx={{
                backgroundColor: 'rgba(255,255,255,0.1)',
                borderRadius: '8px',
                p: 2,
                fontStyle: 'italic',
                flex: 1
              }}>
                {feedback.overall || 'No feedback available'}
              </Typography>
            </CardContent>
          </Card>

          <Card sx={{
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            color: 'white',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            flex: 1,
            display: 'flex',
            flexDirection: 'column'
          }}>
            <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
                ✅ Objectives Completed
              </Typography>
              <List sx={{ backgroundColor: 'rgba(255,255,255,0.3)', borderRadius: '8px', p: 1, flex: 1 }}>
                {objectives_completed.map((objective, index) => (
                  <ListItem key={index} sx={{ px: 0 }}>
                    <ListItemText
                      primary={`🎯 ${objective}`}
                      sx={{
                        '& .MuiListItemText-primary': {
                          fontWeight: 'bold',
                          color: '#2e7d32'
                        }
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)'
          }}>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold' }}>
                📝 Conversation Transcript
              </Typography>
              <Box sx={{
                maxHeight: '300px',
                overflowY: 'auto',
                backgroundColor: 'rgba(255,255,255,0.1)',
                borderRadius: '12px',
                p: 2
              }}>
                {transcript && transcript.map((msg, index) => (
                  <Box key={index} sx={{ mb: 1 }}>
                    <Chip
                      label={`${msg.role === 'user' ? '👤' : '🤖'} ${msg.role}: ${msg.content}`}
                      sx={{
                        backgroundColor: msg.role === 'user' ? 'rgba(255,255,255,0.8)' : 'rgba(255,215,0,0.8)',
                        color: msg.role === 'user' ? '#333' : '#333',
                        fontWeight: 'bold',
                        '&:hover': {
                          backgroundColor: msg.role === 'user' ? 'rgba(255,255,255,1)' : 'rgba(255,215,0,1)'
                        }
                      }}
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Button variant="contained" size="large" onClick={startNewSession}>
          Start New Session
        </Button>
      </Box>
    </Box>
  );
};

export default Feedback;
