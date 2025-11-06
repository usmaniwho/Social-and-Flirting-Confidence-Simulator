import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardContent, Typography, Button, Box, LinearProgress,
  Alert
} from '@mui/material';
import axios from 'axios';

const Calibration = ({ userId }) => {
  const [steps, setSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [countdown, setCountdown] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [completedSteps, setCompletedSteps] = useState([]);
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const countdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCalibrationSteps();
    startVideo();
  }, []);

  const fetchCalibrationSteps = async () => {
    try {
      const res = await axios.get('/api/calibration/steps');
      setSteps(res.data.steps);
    } catch (err) {
      setError('Failed to load calibration steps');
    } finally {
      setLoading(false);
    }
  };

  const startVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      videoRef.current.srcObject = stream;
      videoRef.current.onloadedmetadata = () => {
        videoRef.current.play().catch(err => {
          if (err.name !== 'AbortError') {
            console.error('Video play error:', err);
            setError('Failed to start video playback');
          }
        });
      };
    } catch (err) {
      setError('Failed to access camera and microphone');
    }
  };

  const startRecording = async () => {
    try {
      const stream = videoRef.current.srcObject;
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      const chunks = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        await submitCalibration(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setCountdown(10);

      // Countdown timer
      countdownRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownRef.current);
            if (mediaRecorder.state === 'recording') {
              mediaRecorder.stop();
              setIsRecording(false);
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setError('Failed to start recording');
    }
  };

  const submitCalibration = async (videoBlob) => {
    try {
      // Convert video blob to base64
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64Video = reader.result.split(',')[1]; // Remove data:video/webm;base64, prefix

        // Safety check: ensure current step exists
        if (!steps[currentStep] || !steps[currentStep].step_id) {
          setError('Calibration step not found. Please refresh and try again.');
          return;
        }

        // Send calibration data to backend
        const response = await axios.post('/api/calibrate/step', {
          user_id: userId,
          step_id: steps[currentStep].step_id,
          audio: base64Video, // Using video as audio for now, backend will handle
          video: base64Video
        });

        if (response.data.success) {
          setCompletedSteps([...completedSteps, { step: steps[currentStep], result: { message: 'Step completed successfully', success: true } }]);

          if (currentStep < steps.length - 1) {
            setCurrentStep(currentStep + 1);
          } else {
            // Complete calibration
            await axios.post('/api/calibrate/complete', { user_id: userId });
            navigate('/select-session');
          }
        } else {
          setError(`Calibration failed: ${response.data.message}`);
        }
      };
      reader.readAsDataURL(videoBlob);
    } catch (err) {
      setError('Failed to submit calibration');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  if (loading) {
    return <Typography>Loading calibration steps...</Typography>;
  }

  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <Box sx={{ color: 'white' }}>
      <Typography variant="h4" gutterBottom align="center">
        Let's Get You Calibrated!
      </Typography>
      <Typography variant="body1" gutterBottom align="center">
        We'll set up your voice and expressions with a few simple steps. Ready to shine?
      </Typography>

      <LinearProgress variant="determinate" value={progress} sx={{ mb: 3, height: 10 }} />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
        <Card sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.2)',
          mb: 3,
          maxWidth: 600,
          width: '100%'
        }}>
          <CardContent sx={{ pb: 2 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              📹 Live Video Feed
            </Typography>
            <Box sx={{ backgroundColor: 'white', borderRadius: '8px', p: 1 }}>
              <video
                ref={videoRef}
                autoPlay
                muted
                style={{ width: '100%', borderRadius: '8px', height: '300px', objectFit: 'cover' }}
              />
            </Box>
          </CardContent>
        </Card>

        <Card sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.2)',
          maxWidth: 600,
          width: '100%'
        }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Step {currentStep + 1} of {steps.length}
            </Typography>
            <Typography variant="body1" gutterBottom>
              {steps[currentStep]?.instruction}
            </Typography>
            {steps[currentStep]?.line_to_read && (
              <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                "{steps[currentStep].line_to_read}"
              </Typography>
            )}
            {steps[currentStep]?.expression && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Expression: {steps[currentStep].expression}
              </Typography>
            )}
            {steps[currentStep]?.gesture && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Gesture: {steps[currentStep].gesture}
              </Typography>
            )}

            <Box sx={{ mt: 3 }}>
              <Button
                variant="contained"
                color={isRecording ? "error" : "primary"}
                onClick={isRecording ? stopRecording : startRecording}
                size="large"
                fullWidth
              >
                {isRecording ? 'Stop Recording' : 'Start Recording'}
              </Button>
            </Box>

            {isRecording && (
              <Typography variant="body2" sx={{ mt: 1, color: 'red' }}>
                Recording... ({countdown} seconds remaining)
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      {completedSteps.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Completed Steps:
          </Typography>
          {completedSteps.map((item, index) => (
            <Card key={index} sx={{ mb: 1, backgroundColor: 'rgba(255, 255, 255, 0.8)' }}>
              <CardContent>
                <Typography variant="body2">
                  {item.step.instruction}: {item.result.message}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default Calibration;
