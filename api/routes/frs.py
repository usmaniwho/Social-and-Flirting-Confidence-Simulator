from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from models.models import EmotionData, FRSResult, BaselineData, CalibrationStep, CalibrationData, CalibrateStepRequest
from core.scoring import FRSComputation
from hume_ai.hume_ai_client import HumeStreamClient
from core.baselines import baselines
import asyncio
from typing import Dict, Any, List
import os
import shutil

router = APIRouter()

# In-memory storage for baselines and calibration (use DB in production)
calibration_data: Dict[str, CalibrationData] = {}
active_clients: Dict[str, HumeStreamClient] = {}
# In-memory storage for accumulated FRS scores per session
accumulated_frs: Dict[str, List[Dict[str, Any]]] = {}
# In-memory storage for streaming status per session
streaming_sessions: Dict[str, bool] = {}

# Calibration steps as per task description
calibration_steps = [
    CalibrationStep(
        step_id="line_1",
        instruction="Read aloud in a neutral tone",
        line_to_read="Hey there! I saw you across the room and figured I'd come say hi."
    ),
    CalibrationStep(
        step_id="line_2",
        instruction="Read aloud in a friendly tone",
        line_to_read="Hi! I'm really enjoying this event so far."
    ),
    CalibrationStep(
        step_id="line_3",
        instruction="Read aloud in a flirtatious tone",
        line_to_read="You have such an interesting energy about you."
    ),
    CalibrationStep(
        step_id="line_4",
        instruction="Read aloud in an assertive tone",
        line_to_read="I'd love to continue this conversation if you're free."
    ),
    CalibrationStep(
        step_id="expression_1",
        instruction="Show a genuine smile",
        expression="smiling"
    ),
    CalibrationStep(
        step_id="expression_2",
        instruction="Show curiosity",
        expression="curiosity"
    ),
    CalibrationStep(
        step_id="expression_3",
        instruction="Show playful tone",
        expression="playful"
    ),
    CalibrationStep(
        step_id="expression_4",
        instruction="Show sincere interest",
        expression="sincere_interest"
    ),
    CalibrationStep(
        step_id="gesture_1",
        instruction="Lean in slightly",
        gesture="lean_in"
    ),
    CalibrationStep(
        step_id="gesture_2",
        instruction="Shrug casually",
        gesture="shrug"
    ),
    CalibrationStep(
        step_id="gesture_3",
        instruction="Nod in agreement",
        gesture="nod"
    )
]

@router.get("/calibration/steps")
def get_calibration_steps():
    """
    Get all calibration steps for the initial phase.
    """
    return {"steps": [step.dict() for step in calibration_steps]}



@router.post("/calibrate/step")
async def calibrate_step(request: CalibrateStepRequest):
    """
    Evaluate calibration step using Hume AI.
    Accepts base64 encoded audio and/or video data.
    Only marks step as completed if Hume analysis meets thresholds.
    """
    from hume_ai.hume_ai_client import HumeStreamClient
    import base64

    user_id = request.user_id
    step_id = request.step_id
    audio = request.audio

    if user_id not in calibration_data:
        calibration_data[user_id] = CalibrationData(
            user_id=user_id,
            steps_completed=[],
            baseline_emotions={}
        )

    # Find the step details
    step = next((s for s in calibration_steps if s.step_id == step_id), None)
    if not step:
        raise HTTPException(status_code=400, detail="Invalid step_id")

    # Decode audio/video if provided
    audio_bytes = base64.b64decode(audio) if audio else None
    video_bytes = base64.b64decode(request.video) if request.video else None

    # Use quick_analyze for calibration - requires audio or video data
    client = HumeStreamClient()
    try:
        emotions = await client.quick_analyze(audio_bytes=audio_bytes, video_bytes=video_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Hume analysis failed: {e}. Ensure audio or video data is provided and Hume API is configured.")

    # Check thresholds based on step type
    from core.data_contract import CalibrationThresholds
    success = False
    if step.line_to_read:  # Voice step
        success = emotions.get("vocal_tone", 0) > CalibrationThresholds.VOCAL_TONE_MIN and emotions.get("engagement", 0) > CalibrationThresholds.ENGAGEMENT_VOICE_MIN
    elif step.expression:  # Expression step
        success = emotions.get("smile", 0) > CalibrationThresholds.SMILE_MIN and emotions.get("eye_contact", 0) > CalibrationThresholds.EYE_CONTACT_MIN
    elif step.gesture:  # Gesture step (basic check, could be improved with body data)
        success = emotions.get("engagement", 0) > CalibrationThresholds.ENGAGEMENT_GESTURE_MIN

    if success:
        # Store emotion data for this step
        calibration_data[user_id].baseline_emotions[step_id] = emotions

        # Mark step as completed
        if step_id not in calibration_data[user_id].steps_completed:
            calibration_data[user_id].steps_completed.append(step_id)

        return {"message": f"Step {step_id} calibrated successfully", "completed_steps": calibration_data[user_id].steps_completed, "success": True}
    else:
        return {"message": f"Step {step_id} failed calibration. Emotions detected: {emotions}. Please try again.", "success": False, "emotions": emotions}

@router.post("/calibrate/complete")
def complete_calibration(user_id: str):
    """
    Complete calibration and establish baseline from all steps.
    """
    if user_id not in calibration_data:
        raise HTTPException(status_code=400, detail="No calibration data found")

    cal_data = calibration_data[user_id]
    if len(cal_data.steps_completed) < len(calibration_steps):
        raise HTTPException(status_code=400, detail="Not all calibration steps completed")

    # Calculate baseline as average of all emotion readings
    emotion_keys = ["eye_contact", "smile", "vocal_tone", "pacing", "engagement"]
    baseline_values = {key: 0.0 for key in emotion_keys}

    emotion_steps = list(cal_data.baseline_emotions.keys())  # Now keys are step_ids like "line_1"
    for step_key in emotion_steps:
        step_data = cal_data.baseline_emotions[step_key]
        for key in emotion_keys:
            baseline_values[key] += step_data.get(key, 0.0)

    # Average the values
    num_steps = len(emotion_steps)
    for key in emotion_keys:
        baseline_values[key] /= num_steps

    # Create baseline
    baseline = BaselineData(**baseline_values)
    baselines[user_id] = baseline

    return {"message": "Calibration complete! Baseline established.", "baseline": baseline.dict()}

@router.post("/frs/{user_id}", response_model=FRSResult)
def calculate_frs(user_id: str, data: EmotionData):
    """
    Compute the FRS score from detected emotion metrics, compared to baseline.
    """
    baseline = baselines.get(user_id)
    return FRSComputation.compute_frs(data, baseline)

@router.websocket("/stream/{session_id}")
async def stream_emotions(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time emotion streaming from Hume AI.
    """
    await websocket.accept()
    print(f"WebSocket connection accepted for session {session_id}")

    streaming_sessions[session_id] = True
    is_streaming = True

    try:
        # Initialize Hume client if API key is available
        api_key = os.getenv("HUME_API_KEY")
        client = None
        if api_key:
            try:
                client = HumeStreamClient(api_key=api_key)
                active_clients[session_id] = client
                await client.connect()
            except Exception as e:
                print(f"Failed to initialize Hume client for session {session_id}: {e}")
                client = None
        else:
            print(f"No Hume API key set for session {session_id}. Streaming will not work.")

        # Get session prompt and personality for AI conversation
        from core.session_store import session_store
        from ai_personality import GPTClient
        from core.data_contract import Personality

        session = session_store.get_session(session_id)
        scenario_prompt = session.get('prompt', '') if session else ''
        personality = session.get('personality') if session else None

        gpt_client = None
        if personality:
            try:
                gpt_client = GPTClient()
            except ValueError as e:
                print(f"GPT client initialization failed: {e}. Using default responses.")
        conversation_history = []

        # Send initial AI message based on scenario prompt
        if scenario_prompt:
            ai_response = "Hello! I'm excited to chat with you."  # Default fallback
            if gpt_client and personality:
                try:
                    initial_message = f"Scenario: {scenario_prompt}. Start the conversation as the other person."
                    ai_response = await gpt_client.generate_response(initial_message, Personality(personality))
                    conversation_history.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    print(f"Error generating initial AI response for session {session_id}: {e}. Using default response.")
            await websocket.send_json({"scenario": {"prompt": scenario_prompt, "ai_response": ai_response}})
            print(f"Sent initial scenario prompt and AI message for session {session_id}: {scenario_prompt}, {ai_response}")

        # Callback to send emotion data to frontend
        async def send_to_frontend(emotion_data: Dict[str, Any]):
            if not is_streaming:
                return
            try:
                # Map Hume fields to our EmotionData
                mapped_data = {
                    "eye_contact": emotion_data.get("eye_contact", 0.0),
                    "smile": emotion_data.get("smile", 0.0),
                    "vocal_tone": emotion_data.get("vocal_tone", 0.0),
                    "pacing": emotion_data.get("pacing", 0.0),
                    "engagement": emotion_data.get("engagement", 0.0)
                }

                # Calculate FRS in real-time
                emotion_obj = EmotionData(**mapped_data)
                # Get baseline from session store
                baseline = None
                if session:
                    user_id = session.get('user_id')
                    baseline = baselines.get(user_id)
                frs_result = FRSComputation.compute_frs(emotion_obj, baseline)

                # Accumulate FRS scores for session
                if session_id not in accumulated_frs:
                    accumulated_frs[session_id] = []
                accumulated_frs[session_id].append(frs_result.model_dump())

                # Send combined data
                data_to_send = {
                    "emotions": mapped_data,
                    "frs": frs_result.model_dump()
                }
                await websocket.send_json(data_to_send)
                print(f"Real-time FRS for session {session_id}: {frs_result.frs_score}, emotions: {mapped_data}")
            except Exception as e:
                print(f"Error sending to frontend for session {session_id}: {e}")

        # If Hume client is available, start receiving loop
        if client:
            receive_task = asyncio.create_task(client.receive_loop(send_to_frontend))
        else:
            # No Hume client, cannot stream real data
            await websocket.send_json({"error": "Hume API not configured. Cannot start streaming."})
            await websocket.close()
            return

        # Listen for messages from frontend (user responses or stop signal)
        try:
            while is_streaming:
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)  # Increased timeout
                    if data.get("action") == "stop":
                        print(f"Stop signal received for session {session_id}")
                        is_streaming = False
                        await websocket.close()  # Close the WebSocket immediately
                        break
                    elif "user_message" in data and gpt_client and personality:
                        # Handle user message and generate AI response
                        user_message = data["user_message"]
                        conversation_history.append({"role": "user", "content": user_message})
                        try:
                            ai_response = await gpt_client.generate_response(user_message, Personality(personality), conversation_history)
                            conversation_history.append({"role": "assistant", "content": ai_response})
                            await websocket.send_json({"ai_message": ai_response, "type": "response"})
                            print(f"Sent AI response for session {session_id}: {ai_response}")
                        except Exception as e:
                            print(f"Error generating AI response for session {session_id}: {e}")
                except asyncio.TimeoutError:
                    # No message received, continue
                    pass
        except WebSocketDisconnect:
            print(f"Client for session {session_id} disconnected")
            is_streaming = False

    except WebSocketDisconnect:
        print(f"Client for session {session_id} disconnected")
        is_streaming = False
    except Exception as e:
        print(f"Streaming error for session {session_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        is_streaming = False
        streaming_sessions[session_id] = False
        if session_id in active_clients:
            try:
                await active_clients[session_id].disconnect()
            except Exception as e:
                print(f"Error disconnecting Hume client for session {session_id}: {e}")
            del active_clients[session_id]

@router.get("/streaming/status/{session_id}")
def get_streaming_status(session_id: str):
    """
    Get the current streaming status for a session.
    """
    is_streaming = streaming_sessions.get(session_id, False)
    return {"session_id": session_id, "is_streaming": is_streaming}

@router.get("/feedback/{session_id}")
def get_feedback(session_id: str):
    """
    Get feedback for a session based on accumulated FRS scores.
    """
    # Stop streaming if active
    if session_id in streaming_sessions:
        streaming_sessions[session_id] = False

    # Get accumulated FRS scores
    frs_scores = accumulated_frs.get(session_id, [])
    if not frs_scores:
        return {"message": "No FRS data found for session", "feedback": "No feedback available"}

    # Calculate average FRS score
    avg_frs = sum(score["frs_score"] for score in frs_scores) / len(frs_scores)

    # Generate feedback based on FRS score
    from core.data_contract import FeedbackThresholds
    if avg_frs >= FeedbackThresholds.EXCELLENT_MIN:
        feedback = "Excellent! Your flirting skills are top-notch. You demonstrated strong eye contact, genuine smiles, and engaging vocal tone."
    elif avg_frs >= FeedbackThresholds.GOOD_MIN:
        feedback = "Good job! You showed solid flirting skills with room for improvement in engagement and pacing."
    elif avg_frs >= FeedbackThresholds.DECENT_MIN:
        feedback = "Decent performance. Focus on increasing eye contact and smiling more naturally to improve your FRS."
    else:
        feedback = "There's room for improvement. Practice maintaining eye contact, smiling genuinely, and using a more engaging vocal tone."

    return {
        "message": "Session feedback retrieved successfully",
        "average_frs": round(avg_frs, 2),
        "feedback": feedback,
        "total_readings": len(frs_scores)
    }

@router.post("/session/end/{session_id}")
def end_session(session_id: str):
    """
    End a session and provide feedback based on accumulated FRS scores.
    """
    # Stop streaming if active
    if session_id in streaming_sessions:
        streaming_sessions[session_id] = False

    # Get accumulated FRS scores
    frs_scores = accumulated_frs.get(session_id, [])
    if not frs_scores:
        return {"message": "No FRS data found for session", "feedback": "No feedback available"}

    # Calculate average FRS components
    avg_charisma = sum(score["charisma_friendliness"] for score in frs_scores) / len(frs_scores)
    avg_empathy = sum(score["emotional_attunement_empathy"] for score in frs_scores) / len(frs_scores)
    avg_confidence = sum(score["confidence_selfregulation"] for score in frs_scores) / len(frs_scores)
    avg_listening = sum(score["listening_reciprocal"] for score in frs_scores) / len(frs_scores)
    avg_frs = sum(score["frs_score"] for score in frs_scores) / len(frs_scores)

    # Union of all medals earned
    all_medals = set()
    for score in frs_scores:
        all_medals.update(score["medals"])
    medals_list = list(all_medals)

    # Calculate stars based on average FRS
    if avg_frs >= 9.0:
        stars_earned = 5
    elif avg_frs >= 8.0:
        stars_earned = 4
    elif avg_frs >= 7.0:
        stars_earned = 3
    elif avg_frs >= 6.0:
        stars_earned = 2
    elif avg_frs >= 5.0:
        stars_earned = 1
    else:
        stars_earned = 0

    # Generate feedback based on FRS score
    from core.data_contract import FeedbackThresholds
    if avg_frs >= FeedbackThresholds.EXCELLENT_MIN:
        feedback = "Excellent! Your flirting skills are top-notch. You demonstrated strong eye contact, genuine smiles, and engaging vocal tone."
    elif avg_frs >= FeedbackThresholds.GOOD_MIN:
        feedback = "Good job! You showed solid flirting skills with room for improvement in engagement and pacing."
    elif avg_frs >= FeedbackThresholds.DECENT_MIN:
        feedback = "Decent performance. Focus on increasing eye contact and smiling more naturally to improve your FRS."
    else:
        feedback = "There's room for improvement. Practice maintaining eye contact, smiling genuinely, and using a more engaging vocal tone."

    # Get transcript from session store
    from core.session_store import session_store
    transcript = session_store.get_full_transcript(session_id)

    # Create full FRSResult
    from models.models import FRSResult
    final_frs = FRSResult(
        charisma_friendliness=round(avg_charisma, 2),
        emotional_attunement_empathy=round(avg_empathy, 2),
        confidence_selfregulation=round(avg_confidence, 2),
        listening_reciprocal=round(avg_listening, 2),
        frs_score=round(avg_frs, 2),
        medals=medals_list,
        stars_earned=stars_earned
    )

    return {
        "message": "Session ended successfully",
        "final_frs": final_frs.model_dump(),
        "feedback": {"overall": feedback},
        "objectives_completed": [],  # Placeholder, can be implemented later
        "stars_earned": stars_earned,
        "transcript": transcript,
        "total_readings": len(frs_scores)
    }

@router.post("/upload_video")
async def upload_video(user_id: str, file: UploadFile = File(...)):
    """
    Upload a video file for emotion analysis and FRS computation.
    """
    # Validate file type
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only video files are allowed.")

    # Save the uploaded file
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{user_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Use Hume AI batch analysis for real emotion detection
    client = HumeStreamClient()
    try:
        with open(file_path, "rb") as f:
            video_bytes = f.read()
        emotions = await client.quick_analyze(video_bytes=video_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Hume video analysis failed: {e}")

    # Compute FRS
    emotion_obj = EmotionData(**emotions)
    baseline = baselines.get(user_id)
    frs_result = FRSComputation.compute_frs(emotion_obj, baseline)

    return {
        "message": "Video processed successfully",
        "file_path": file_path,
        "aggregated_emotions": emotions,
        "frs_result": frs_result.dict()
    }
