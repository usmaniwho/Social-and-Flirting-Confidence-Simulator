# TODO: Integrate Hume AI Evaluation for Calibration Steps

## Overview
Modify the calibration process to use Hume AI for evaluating each step. Only advance to the next step if Hume confirms calibration, and only start sessions after all calibration steps are fulfilled.

## Steps to Complete

### 1. Define Calibration Thresholds
- Define success criteria for each type of calibration step (voice, expression, gesture) based on Hume metrics.
  - Voice steps (line_1 to line_4): vocal_tone > 0.5, engagement > 0.6
  - Expression steps (expression_1 to expression_4): smile > 0.7, eye_contact > 0.6
  - Gesture steps (gesture_1 to gesture_3): Use body data if available, e.g., posture > 0.5 or specific gesture detection.

### 2. Update /calibrate/step Endpoint in api/routes/frs.py
- Modify the endpoint to accept audio/video data (base64 encoded).
- Decode and analyze with Hume quick_analyze.
- Check metrics against step-specific thresholds.
- Only mark step as completed if thresholds are met; return success/failure response.
- Store calibration data per user.

### 3. Update Frontend Calibration in static/index.html
- For each step, prompt user to perform the action (read line, show expression, perform gesture).
- Capture audio/video using getUserMedia.
- Send captured data to /calibrate/step via POST.
- Display result: if failed, show retry button; if passed, advance to next step.
- Only show "Complete Calibration" after all steps are passed.

### 4. Modify /start Endpoint in api/routes/session.py
- Before starting a session, check if the user has completed all calibration steps.
- If not, return an error or redirect to calibration.
- Use calibration_data or session_store to verify completion.

### 5. Update Session Store for Calibration Status
- Modify core/session_store.py to persist calibration status per user (e.g., completed_steps list).
- Ensure calibration data is stored across sessions.

### 6. Handle Errors and Fallbacks
- If Hume analysis fails, provide fallback (e.g., simulate success for testing) or notify user.
- Add error handling in frontend and backend.

### 7. Test Integration
- Test Hume API integration.
- Verify frontend captures and sends data correctly.
- Ensure sessions only start after full calibration.
- Test edge cases: Hume failure, user retry, etc.

## Progress Tracking
- [ ] Step 1: Define thresholds
- [ ] Step 2: Update /calibrate/step
- [ ] Step 3: Update frontend
- [ ] Step 4: Modify /start
- [ ] Step 5: Update session store
- [ ] Step 6: Error handling
- [ ] Step 7: Testing
