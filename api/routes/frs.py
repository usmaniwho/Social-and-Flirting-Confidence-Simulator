from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from models.models import EmotionData, FRSResult, BaselineData
from core.scoring import FRSComputation
from hume_ai.hume_ai_client import HumeStreamClient
import asyncio
from typing import Dict, Any
import os
import shutil

router = APIRouter()

# In-memory storage for baselines (use DB in production)
baselines: Dict[str, BaselineData] = {}
active_clients: Dict[str, HumeStreamClient] = {}

@router.post("/calibrate")
def calibrate_baseline(user_id: str, data: EmotionData):
    """
    Establish user baseline from calibration data.
    """
    baseline = BaselineData(
        eye_contact=data.eye_contact,
        smile=data.smile,
        vocal_tone=data.vocal_tone,
        pacing=data.pacing,
        engagement=data.engagement
    )
    baselines[user_id] = baseline
    return {"message": "Baseline established", "baseline": baseline.dict()}

@router.post("/frs/{user_id}", response_model=FRSResult)
def calculate_frs(user_id: str, data: EmotionData):
    """
    Compute the FRS score from detected emotion metrics, compared to baseline.
    """
    baseline = baselines.get(user_id)
    return FRSComputation.compute_frs(data, baseline)

@router.websocket("/stream/{user_id}")
async def stream_emotions(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time emotion streaming from Hume AI.
    """
    await websocket.accept()
    print(f"WebSocket connection accepted for user {user_id}")

    simulation_task = None

    try:
        # Initialize Hume client
        api_key = os.getenv("HUME_API_KEY")
        if not api_key:
            await websocket.send_json({"error": "HUME_API_KEY environment variable not set"})
            return

        client = HumeStreamClient(api_key=api_key)
        active_clients[user_id] = client

        await client.connect()

        # Callback to send emotion data to frontend
        async def send_to_frontend(emotion_data: Dict[str, Any]):
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
                baseline = baselines.get(user_id)
                frs_result = FRSComputation.compute_frs(emotion_obj, baseline)

                # Send combined data
                data_to_send = {
                    "emotions": mapped_data,
                    "frs": frs_result.dict()
                }
                await websocket.send_json(data_to_send)
                print(f"Sent data to frontend for {user_id}: emotions={mapped_data}, frs={frs_result.frs_score}")
            except Exception as e:
                print(f"Error sending to frontend for {user_id}: {e}")

        # Start receiving from Hume AI
        # For testing without actual webcam data, simulate emotion data
        async def simulate_emotion_data():
            import random
            import asyncio

            while True:
                # Simulate realistic emotion data
                emotion_data = {
                    "eye_contact": random.uniform(0.3, 0.9),
                    "smile": random.uniform(0.2, 0.8),
                    "vocal_tone": random.uniform(0.4, 0.9),
                    "pacing": random.uniform(0.3, 0.8),
                    "engagement": random.uniform(0.5, 0.95)
                }

                print(f"Simulating emotion data for {user_id}: {emotion_data}")
                await send_to_frontend(emotion_data)
                await asyncio.sleep(1)  # Send data every second

        # Start simulation for testing as a cancellable task
        simulation_task = asyncio.create_task(simulate_emotion_data())
        await simulation_task

    except WebSocketDisconnect:
        print(f"Client {user_id} disconnected")
    except Exception as e:
        print(f"Streaming error for {user_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        if simulation_task and not simulation_task.done():
            simulation_task.cancel()
            try:
                await simulation_task
            except asyncio.CancelledError:
                print(f"Simulation task cancelled for {user_id}")
        if user_id in active_clients:
            try:
                await active_clients[user_id].disconnect()
            except:
                pass
            del active_clients[user_id]

@router.post("/upload_video")
async def upload_video(user_id: str, file: UploadFile = File(...)):
    """
    Upload a video file for emotion analysis and FRS computation.
    """
    # Validate file type
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only video files are allowed.")

    # Save the uploaded file
    file_path = f"uploads/{user_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # For now, simulate processing since Hume AI client doesn't support video processing directly
    # In a real implementation, you'd integrate with Hume's batch API or similar
    import random
    import time

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
