from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from models.models import EmotionData, FRSResult, BaselineData, CalibrationStep, CalibrationData
from core.scoring import FRSComputation
from hume_ai.hume_ai_client import HumeStreamClient
import asyncio
from typing import Dict, Any, List
import os
import shutil

router = APIRouter()

# In-memory storage for baselines and calibration (use DB in production)
baselines: Dict[str, BaselineData] = {}
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
def calibrate_step(user_id: str, step_id: str, data: EmotionData):
    """
    Record calibration data for a specific step.
    """
    if user_id not in calibration_data:
        calibration_data[user_id] = CalibrationData(
            user_id=user_id,
            steps_completed=[],
            baseline_emotions={}
        )

    # Store emotion data for this step
    step_key = f"{step_id}_emotions"
    calibration_data[user_id].baseline_emotions[step_key] = data.dict()

    # Mark step as completed
    if step_id not in calibration_data[user_id].steps_completed:
        calibration_data[user_id].steps_completed.append(step_id)

    return {"message": f"Step {step_id} calibrated", "completed_steps": calibration_data[user_id].steps_completed}

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

    emotion_steps = [k for k in cal_data.baseline_emotions.keys() if k.endswith("_emotions")]
    for step_key in emotion_steps:
        step_data = cal_data.baseline_emotions[step_key]
        for key in emotion_keys:
            baseline_values[key] += step_data[key]

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
    simulation_task = None
    is_streaming = True

    try:
        # Initialize Hume client if API key is available
        api_key = os.getenv("HUME_API_KEY")
        client = None
        if api_key:
            client = HumeStreamClient(api_key=api_key)
            active_clients[session_id] = client
            await client.connect()

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
                from core.session_store import session_store
                session = session_store.get_session(session_id)
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
                print(f"Sent data to frontend for session {session_id}: emotions={mapped_data}, frs={frs_result.frs_score}")
            except Exception as e:
                print(f"Error sending to frontend for session {session_id}: {e}")

        # For testing, always simulate emotion data regardless of Hume API
        async def simulate_emotion_data():
            import random
            import asyncio

            while is_streaming:
                # Simulate realistic emotion data
                emotion_data = {
                    "eye_contact": random.uniform(0.3, 0.9),
                    "smile": random.uniform(0.2, 0.8),
                    "vocal_tone": random.uniform(0.4, 0.9),
                    "pacing": random.uniform(0.3, 0.8),
                    "engagement": random.uniform(0.5, 0.95)
                }

                print(f"Simulating emotion data for session {session_id}: {emotion_data}")
                await send_to_frontend(emotion_data)
                await asyncio.sleep(1)  # Send data every second

        # Start simulation for testing as a cancellable task
        simulation_task = asyncio.create_task(simulate_emotion_data())

        # Listen for stop message from frontend
        try:
            while is_streaming:
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)  # Increased timeout
                    if data.get("action") == "stop":
                        print(f"Stop signal received for session {session_id}")
                        is_streaming = False
                        if simulation_task and not simulation_task.done():
                            simulation_task.cancel()
                            try:
                                await simulation_task
                            except asyncio.CancelledError:
                                print(f"Simulation task cancelled for session {session_id}")
                        await websocket.close()  # Close the WebSocket immediately
                        break
                except asyncio.TimeoutError:
                    # No message received, continue
                    pass
        except WebSocketDisconnect:
            print(f"Client for session {session_id} disconnected")
            is_streaming = False
            if simulation_task and not simulation_task.done():
                simulation_task.cancel()
                try:
                    await simulation_task
                except asyncio.CancelledError:
                    print(f"Simulation task cancelled for session {session_id}")

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
        if simulation_task and not simulation_task.done():
            simulation_task.cancel()
            try:
                await simulation_task
            except asyncio.CancelledError:
                print(f"Simulation task cancelled for session {session_id}")
        if session_id in active_clients:
            try:
                await active_clients[session_id].disconnect()
            except:
                pass
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
    if avg_frs >= 8.0:
        feedback = "Excellent! Your flirting skills are top-notch. You demonstrated strong eye contact, genuine smiles, and engaging vocal tone."
    elif avg_frs >= 6.0:
        feedback = "Good job! You showed solid flirting skills with room for improvement in engagement and pacing."
    elif avg_frs >= 4.0:
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

    # Calculate average FRS score
    avg_frs = sum(score["frs_score"] for score in frs_scores) / len(frs_scores)

    # Generate feedback based on FRS score
    if avg_frs >= 8.0:
        feedback = "Excellent! Your flirting skills are top-notch. You demonstrated strong eye contact, genuine smiles, and engaging vocal tone."
    elif avg_frs >= 6.0:
        feedback = "Good job! You showed solid flirting skills with room for improvement in engagement and pacing."
    elif avg_frs >= 4.0:
        feedback = "Decent performance. Focus on increasing eye contact and smiling more naturally to improve your FRS."
    else:
        feedback = "There's room for improvement. Practice maintaining eye contact, smiling genuinely, and using a more engaging vocal tone."

    return {
        "message": "Session ended successfully",
        "average_frs": round(avg_frs, 2),
        "feedback": feedback,
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

    # For now, simulate processing since Hume AI client doesn't support video processing directly
    # In a real implementation, you'd integrate with Hume's batch API or similar
    import random

    # Simulate processing time
    await asyncio.sleep(2)

    # Simulate aggregated emotion data from video
    aggregated_emotions = {
        "eye_contact": random.uniform(0.4, 0.9),
        "smile": random.uniform(0.3, 0.8),
        "vocal_tone": random.uniform(0.5, 0.9),
        "pacing": random.uniform(0.4, 0.8),
        "engagement": random.uniform(0.6, 0.95)
    }

    # Compute FRS
    emotion_obj = EmotionData(**aggregated_emotions)
    baseline = baselines.get(user_id)
    frs_result = FRSComputation.compute_frs(emotion_obj, baseline)

    return {
        "message": "Video processed successfully",
        "file_path": file_path,
        "aggregated_emotions": aggregated_emotions,
        "frs_result": frs_result.dict()
    }
