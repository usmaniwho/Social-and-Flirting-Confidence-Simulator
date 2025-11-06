import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardContent, Typography, Button, Grid, Box
} from '@mui/material';

const Home = ({ userId, setSessionId }) => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const startJourney = async () => {
    setLoading(true);

    // Simulate starting a default session or just navigate to calibration
    // For now, we'll navigate directly to calibration
    navigate('/calibration');
  };

  return (
    <Box sx={{ textAlign: 'center', color: 'white', minHeight: '80vh', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: 'bold', mb: 2 }}>
        🚀 Welcome to Your Social Skills Journey!
      </Typography>
      <Typography variant="h5" gutterBottom sx={{ mb: 4, opacity: 0.9 }}>
        Build confidence through realistic conversations and personalized feedback
      </Typography>

      <Grid container spacing={3} justifyContent="center" sx={{ mt: 4 }}>
        <Grid item xs={12} md={8}>
          <Card sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            borderRadius: '24px',
            boxShadow: '0 12px 40px rgba(0,0,0,0.4)',
            border: '2px solid rgba(255,255,255,0.3)',
            p: 4
          }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
                🎯 Ready to Level Up Your Social Skills?
              </Typography>
              <Typography variant="h6" gutterBottom sx={{ mb: 4, opacity: 0.9 }}>
                Start your personalized training session with AI-powered conversations and real-time feedback
              </Typography>

              <Button
                variant="contained"
                size="large"
                onClick={startJourney}
                disabled={loading}
                sx={{
                  minWidth: 300,
                  minHeight: 80,
                  fontSize: '1.5rem',
                  fontWeight: 'bold',
                  borderRadius: '16px',
                  background: 'linear-gradient(45deg, #FF6B6B 30%, #4ECDC4 90%)',
                  boxShadow: '0 8px 32px rgba(255,107,107,0.3)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #FF5252 30%, #26D0CE 90%)',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 12px 40px rgba(255,107,107,0.4)',
                  },
                  transition: 'all 0.3s ease'
                }}
              >
                {loading ? '🚀 Starting...' : '🚀 Start Your Journey'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Home;
