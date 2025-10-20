import os
import asyncio
import json
import tempfile
from hume import AsyncHumeClient
from hume.expression_measurement.stream import Config as EmConfig
from hume.expression_measurement.stream.socket_client import StreamConnectOptions
from hume.expression_measurement.stream import StreamFace, StreamLanguage
from dotenv import load_dotenv

load_dotenv()


class HumeStreamClient:
    """
    Handles real-time multimodal emotional analysis using Hume AI’s Streaming API.
    Supports:
      - 🎙️ Audio stream (language tone, pacing, engagement)
      - 🎥 Face stream (eye contact, smile, expression)
      - 💃 Optional body stream (posture, gestures)
    """

    def __init__(self, api_key: str = None):
        # ✅ Load Hume API key from .env or passed argument
        self.api_key = api_key or os.getenv("HUME_API_KEY")
        if not self.api_key:
            raise ValueError("HUME_API_KEY environment variable not set")

        print(f"HumeStreamClient initialized with API key")
        self.client = AsyncHumeClient(api_key=self.api_key)

        # ✅ Configure face + language models for emotion measurement
        self.config = EmConfig(
            face=StreamFace(),
            language=StreamLanguage()
        )

    async def connect(self):
        """
        Establish connection with Hume’s real-time stream endpoint.
        Enters the context manager and stores the socket for reuse.
        """
        options = StreamConnectOptions(config=self.config)
        self.stream_cm = self.client.expression_measurement.stream.connect(options=options)
        self.socket = await self.stream_cm.__aenter__()
        return self.socket

    async def disconnect(self):
        """
        Disconnect cleanly from the stream (handled automatically by context manager).
        """
        pass

    async def receive_loop(self, on_emotion_callback):
        """
        🔄 Continuous async loop that listens for live emotion predictions
        and passes them to `on_emotion_callback` for handling.

        Each message includes face and voice predictions.
        """
        try:
            async for msg in self.socket:
                # Hume returns both face and speech predictions in one payload
                face_pred = msg.face.predictions if msg.face else []
                speech_pred = msg.speech.predictions if msg.speech else []

                # 🔹 CHANGED: Gather raw emotional metrics (face + speech)
                val = {
                    "eye_contact": self._map_face_score(face_pred, "EyeContact"),
                    "smile": self._map_face_score(face_pred, "Smile"),
                    "vocal_tone": self._map_speech_score(speech_pred, "VocalTone"),
                    "pacing": self._map_speech_score(speech_pred, "Pacing"),
                    "engagement": self._map_speech_score(speech_pred, "Engagement"),
                }

                # 🔹 CHANGED: Fuse multimodal data → infer general emotion label
                val["emotion_state"] = self._infer_emotion_state(val)

                # ✅ Pass the processed emotion metrics to the callback (FRS update, GPT modulation, etc.)
                on_emotion_callback(val)

        except Exception as e:
            print(f"Streaming error: {e}")
            # Continue without crashing the main WebSocket handler

    # ===============================
    # 🔍 Helper Mapping Functions
    # ===============================
    def _map_face_score(self, predictions, target_name):
        # Find specific facial emotion or feature score
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    def _map_speech_score(self, predictions, target_name):
        # Find voice/emotion metric score
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    def _map_body_score(self, predictions, target_name):
        # Placeholder for future body gesture mapping
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    # ===============================
    # 🧠 Emotion Fusion Logic
    # ===============================
    def _infer_emotion_state(self, val: dict) -> str:
        """
        Fuse face, voice, and posture metrics into a simplified emotional label.
        (Heuristic model that you can later replace with ML fusion.)
        """
        smile = val.get("smile", 0)
        eye_contact = val.get("eye_contact", 0)
        vocal_tone = val.get("vocal_tone", 0)
        engagement = val.get("engagement", 0)

        # Basic emotion fusion heuristic
        if smile > 0.6 and vocal_tone > 0.5:
            return "happy"
        if engagement > 0.6:
            return "focused"
        if vocal_tone < 0.3 and eye_contact < 0.3:
            return "disengaged"
        if vocal_tone > 0.6:
            return "excited"
        if smile < 0.2 and vocal_tone < 0.3:
            return "stressed"
        return "neutral"

    # ===============================
    # 📤 Sending Live Data
    # ===============================
    async def send_webcam_data(self, webcam_data: bytes):
        """
        Send webcam (face) data to Hume for analysis.
        """
        try:
            if self.socket:
                await self.socket.send_face(webcam_data)
        except Exception as e:
            print(f"Error sending webcam data to Hume: {e}")

    async def send_mic_data(self, mic_data: bytes):
        """
        Send microphone (audio) data to Hume for analysis.
        Uses quick_analyze for simulated audio emotion evaluation.
        TODO: Integrate with Hume's audio analysis API when batch parameters are resolved.
        """
        try:
            if mic_data:
                # Use quick_analyze for audio emotion evaluation (simulated for now)
                emotions = await self.quick_analyze(audio_bytes=mic_data)
                # Update the callback with audio-only emotions (face data comes from streaming)
                if emotions:
                    # Merge with current emotions if available
                    # For now, just print - in production, you'd want to merge properly
                    print(f"Audio emotions: {emotions}")
        except Exception as e:
            print(f"Error sending audio to Hume: {e}")

    async def _analyze_audio_batch(self, audio_bytes: bytes) -> dict:
        """
        Analyze audio using Hume's batch emotion measurement API.
        """
        try:
            # Save to temp file for batch API
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            # Use Hume batch API for emotion measurement
            job = await self.client.expression_measurement.batch.start_inference_job(
                files=[temp_file_path],
                models={
                    "language": {}
                }
            )

            # Wait for completion (in production, you'd poll or use webhooks)
            await job.await_complete()

            # Get predictions
            predictions = await job.get_predictions()

            # Clean up
            os.unlink(temp_file_path)

            # Extract speech emotions
            speech_emotions = {}
            if predictions and len(predictions) > 0:
                pred = predictions[0]
                if hasattr(pred, 'language') and pred.language:
                    for emotion in pred.language.predictions:
                        if emotion.name == "VocalTone":
                            speech_emotions["vocal_tone"] = emotion.score
                        elif emotion.name == "Pacing":
                            speech_emotions["pacing"] = emotion.score
                        elif emotion.name == "Engagement":
                            speech_emotions["engagement"] = emotion.score

            return speech_emotions

        except Exception as e:
            print(f"Batch audio analysis error: {e}")
            return {}

    async def send_body_data(self, body_frame: bytes):
        """
        Send skeletal/body motion data for gesture/posture analysis.
        """
        try:
            if self.socket:
                await self.socket.send_body(body_frame)
        except Exception as e:
            print(f"Error sending body data to Hume: {e}")

    async def quick_analyze(self, audio_bytes: bytes = None, body_data: dict = None) -> dict:
        """
        Quick analysis method for non-streaming use cases.
        Returns emotion metrics without maintaining a persistent stream.
        """
        # For now, return simulated data since Hume streaming is complex
        # In production, implement proper Hume analysis
        import random
        return {
            "eye_contact": random.uniform(0.3, 0.9),
            "smile": random.uniform(0.2, 0.8),
            "vocal_tone": random.uniform(0.4, 0.9),
            "pacing": random.uniform(0.3, 0.8),
            "engagement": random.uniform(0.5, 0.95),
            "emotion_state": random.choice(["happy", "focused", "neutral", "excited"])
        }
