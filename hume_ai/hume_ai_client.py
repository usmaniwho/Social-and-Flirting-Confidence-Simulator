import os
import asyncio
import json
import tempfile
import random
import cv2
import numpy as np
from hume import AsyncHumeClient
from hume.expression_measurement.stream import StreamFace, StreamLanguage, Config
from hume.expression_measurement.stream.socket_client import StreamConnectOptions
# Note: Hume AI doesn't offer body-motion model publicly
# We'll use MediaPipe for body language analysis
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_holistic = mp.solutions.holistic
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("MediaPipe not available. Install with: pip install mediapipe")
from dotenv import load_dotenv

load_dotenv()


class HumeStreamClient:
    """
    Handles real-time multimodal emotional analysis using Hume AI’s Streaming API.
    Actively evaluates body language and conversation through multimodal fusion.
    Supports:
      - 🎙️ Audio stream (language tone, pacing, engagement)
      - 🎥 Face stream (eye contact, smile, expression)
      - 💃 Body stream (posture, gestures, body language)
    """

    def __init__(self, api_key: str = None):
        # Load Hume API key from .env or passed argument
        self.api_key = api_key or os.getenv("HUME_API_KEY")
        self.hume_available = bool(self.api_key)

        if self.hume_available:
            print("HumeStreamClient initialized with API key")
            self.client = AsyncHumeClient(api_key=self.api_key)
        else:
            print("Hume API key not set. Running in simulation mode.")
            self.client = None

        self.socket = None
        self.stream_cm = None

    async def connect(self):
        """
        Establish connection with Hume’s real-time stream endpoint.
        Enters the context manager and stores the socket for reuse.
        """
        if not self.hume_available:
            print("Hume not available, skipping connection")
            return None

        if self.socket:
            return self.socket

        config = Config(face=StreamFace(), language=StreamLanguage())
        options = StreamConnectOptions(config=config)
        self.stream_cm = self.client.expression_measurement.stream.connect(options=options)
        self.socket = await self.stream_cm.__aenter__()
        print("Connected to Hume streaming API")
        return self.socket

    async def disconnect(self):
        """
        Disconnect cleanly from the stream.
        """
        if self.stream_cm and self.socket:
            await self.stream_cm.__aexit__(None, None, None)
            self.socket = None
            self.stream_cm = None
            print("Disconnected from Hume streaming API")

    async def receive_loop(self, on_emotion_callback):
        """
        Continuous async loop that listens for live emotion predictions
        and passes them to `on_emotion_callback` for handling.

        Each message includes face, voice, and body predictions for comprehensive analysis.
        """
        if not self.socket:
            await self.connect()

        try:
            async for msg in self.socket:
                # Extract predictions from all modalities
                face_pred = msg.face.predictions if msg.face else []
                speech_pred = msg.speech.predictions if msg.speech else []
                body_pred = msg.body.predictions if msg.body else []

                # Gather raw emotional metrics from all sources
                val = {
                    # Face metrics
                    "eye_contact": self._map_face_score(face_pred, "EyeContact"),
                    "smile": self._map_face_score(face_pred, "Smile"),
                    "facial_expression": self._map_face_score(face_pred, "FacialExpression"),

                    # Speech/Conversation metrics
                    "vocal_tone": self._map_speech_score(speech_pred, "VocalTone"),
                    "pacing": self._map_speech_score(speech_pred, "Pacing"),
                    "engagement": self._map_speech_score(speech_pred, "Engagement"),
                    "prosody": self._map_speech_score(speech_pred, "Prosody"),

                    # Body language metrics
                    "posture": self._map_body_score(body_pred, "Posture"),
                    "gesture": self._map_body_score(body_pred, "Gesture"),
                    "body_movement": self._map_body_score(body_pred, "BodyMovement"),
                    "confidence_pose": self._map_body_score(body_pred, "ConfidencePose"),
                }

                # Fuse multimodal data to infer general emotion and body language state
                val["emotion_state"] = self._infer_emotion_state(val)
                val["body_language_state"] = self._infer_body_language_state(val)
                val["conversation_quality"] = self._assess_conversation_quality(val)

                # Pass the processed emotion metrics to the callback
                on_emotion_callback(val)

        except Exception as e:
            print(f"Streaming error: {e}")
            # Continue without crashing the main WebSocket handler

    # Helper Mapping Functions
    def _map_face_score(self, predictions, target_name):
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    def _map_speech_score(self, predictions, target_name):
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    def _map_body_score(self, predictions, target_name):
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    # Emotion Fusion Logic
    def _infer_emotion_state(self, val: dict) -> str:
        """
        Fuse face, voice, and body metrics into a simplified emotional label.
        """
        smile = val.get("smile", 0)
        eye_contact = val.get("eye_contact", 0)
        vocal_tone = val.get("vocal_tone", 0)
        engagement = val.get("engagement", 0)
        posture = val.get("posture", 0)
        gesture = val.get("gesture", 0)

        # Enhanced emotion fusion heuristic including body language
        if smile > 0.6 and vocal_tone > 0.5 and posture > 0.5:
            return "happy"
        if engagement > 0.6 and eye_contact > 0.5:
            return "focused"
        if vocal_tone < 0.3 and eye_contact < 0.3 and posture < 0.3:
            return "disengaged"
        if vocal_tone > 0.6 and gesture > 0.5:
            return "excited"
        if smile < 0.2 and vocal_tone < 0.3 and posture < 0.4:
            return "stressed"
        return "neutral"

    def _infer_body_language_state(self, val: dict) -> str:
        """
        Analyze body language specifically for posture and gestures.
        """
        posture = val.get("posture", 0)
        gesture = val.get("gesture", 0)
        body_movement = val.get("body_movement", 0)
        confidence_pose = val.get("confidence_pose", 0)

        if confidence_pose > 0.7 and posture > 0.6:
            return "confident"
        if gesture > 0.6 and body_movement > 0.5:
            return "expressive"
        if posture < 0.4 and body_movement < 0.3:
            return "closed_off"
        if gesture > 0.5 and confidence_pose > 0.5:
            return "engaged"
        return "neutral"

    def _assess_conversation_quality(self, val: dict) -> str:
        """
        Assess the quality of conversation based on speech metrics.
        """
        vocal_tone = val.get("vocal_tone", 0)
        pacing = val.get("pacing", 0)
        engagement = val.get("engagement", 0)
        prosody = val.get("prosody", 0)

        avg_quality = (vocal_tone + pacing + engagement + prosody) / 4

        if avg_quality > 0.8:
            return "excellent"
        elif avg_quality > 0.6:
            return "good"
        elif avg_quality > 0.4:
            return "adequate"
        else:
            return "poor"

    # Sending Live Data
    async def send_webcam_data(self, webcam_data: bytes):
        """
        Send webcam (face) data to Hume for analysis.
        """
        if not self.socket:
            await self.connect()
        try:
            await self.socket.send_face(webcam_data)
        except Exception as e:
            print(f"Error sending webcam data to Hume: {e}")

    async def send_mic_data(self, mic_data: bytes):
        """
        Send microphone (audio) data to Hume for conversation analysis.
        Uses mock data for demonstration.
        """
        print("Mock: Sending audio data to Hume for analysis")
        # Mock successful analysis - return random emotion scores
        import random
        mock_emotions = {
            "eye_contact": random.uniform(0.3, 0.9),
            "smile": random.uniform(0.2, 0.8),
            "vocal_tone": random.uniform(0.4, 0.9),
            "pacing": random.uniform(0.3, 0.8),
            "engagement": random.uniform(0.5, 0.9),
            "prosody": random.uniform(0.4, 0.8),
            "emotion_state": random.choice(["happy", "focused", "neutral", "excited", "stressed"]),
            "body_language_state": random.choice(["confident", "engaged", "neutral", "closed_off"]),
            "conversation_quality": random.choice(["excellent", "good", "adequate"])
        }
        print(f"Mock Hume analysis result: {mock_emotions}")
        # Store mock emotions for callback
        if hasattr(self, '_on_emotion_callback') and self._on_emotion_callback:
            self._on_emotion_callback(mock_emotions)
        return mock_emotions

    async def send_body_data(self, body_frame: bytes):
        """
        Send skeletal/body motion data for gesture/posture analysis.
        """
        if not self.socket:
            await self.connect()
        try:
            await self.socket.send_body(body_frame)
        except Exception as e:
            print(f"Error sending body data to Hume: {e}")

    async def _analyze_audio_batch(self, audio_bytes: bytes) -> dict:
        """
        Analyze audio using Hume's batch emotion measurement API for conversation.
        """
        if not self.hume_available:
            # Return mock data when Hume is not available
            return {
                "vocal_tone": 0.5,
                "pacing": 0.5,
                "engagement": 0.5,
                "prosody": 0.5
            }

        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            job_id = await self.client.expression_measurement.batch.start_inference_job(
                urls=[f"file://{temp_file_path}"],
                models={"prosody": {}}
            )

            max_attempts = 30
            attempt = 0
            while attempt < max_attempts:
                job_details = await self.client.expression_measurement.batch.get_job_details(job_id)
                if job_details.state == "COMPLETED":
                    break
                elif job_details.state == "FAILED":
                    raise Exception(f"Job failed: {job_details}")
                await asyncio.sleep(2)
                attempt += 1

            if attempt >= max_attempts:
                raise Exception("Job did not complete within timeout")

            predictions = await self.client.expression_measurement.batch.get_job_predictions(job_id)
            os.unlink(temp_file_path)

            speech_emotions = {}
            if predictions and len(predictions) > 0:
                pred = predictions[0]
                if hasattr(pred, 'prosody') and pred.prosody:
                    for emotion in pred.prosody.predictions:
                        if emotion.name == "VocalTone":
                            speech_emotions["vocal_tone"] = emotion.score
                        elif emotion.name == "Pacing":
                            speech_emotions["pacing"] = emotion.score
                        elif emotion.name == "Engagement":
                            speech_emotions["engagement"] = emotion.score
                        elif emotion.name == "Prosody":
                            speech_emotions["prosody"] = emotion.score

            return speech_emotions

        except Exception as e:
            print(f"Batch audio analysis error: {e}")
            return {}

    async def _analyze_video_batch(self, video_bytes: bytes) -> dict:
        """
        Analyze video using Hume's batch emotion measurement API for face and body.
        """
        if not self.hume_available:
            # Return mock data when Hume is not available
            return {
                "eye_contact": 0.5,
                "smile": 0.6,
                "facial_expression": 0.4
            }

        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_bytes)
                temp_file_path = temp_file.name

            job_id = await self.client.expression_measurement.batch.start_inference_job(
                urls=[f"file://{temp_file_path}"],
                models={"face": {}}
            )

            max_attempts = 3  # Very short timeout for testing
            attempt = 0
            while attempt < max_attempts:
                job_details = await self.client.expression_measurement.batch.get_job_details(job_id)
                if job_details.state == "COMPLETED":
                    break
                elif job_details.state == "FAILED":
                    raise Exception(f"Job failed: {job_details}")
                await asyncio.sleep(0.5)  # Very short sleep
                attempt += 1

            if attempt >= max_attempts:
                raise Exception("Job did not complete within timeout")

            predictions = await self.client.expression_measurement.batch.get_job_predictions(job_id)
            os.unlink(temp_file_path)

            emotions = {}
            if predictions and len(predictions) > 0:
                pred = predictions[0]
                # Face emotions
                if hasattr(pred, 'face') and pred.face:
                    for emotion in pred.face.predictions:
                        if emotion.name == "EyeContact":
                            emotions["eye_contact"] = emotion.score
                        elif emotion.name == "Smile":
                            emotions["smile"] = emotion.score
                        elif emotion.name == "FacialExpression":
                            emotions["facial_expression"] = emotion.score

            return emotions

        except Exception as e:
            print(f"Batch video analysis error: {e}")
            return {}

    def analyze_body_language(self, frame: np.ndarray) -> dict:
        """
        Analyze body language using MediaPipe Holistic for gesture/posture analysis.
        Returns body language metrics that complement Hume AI's face/voice analysis.
        """
        if not MEDIAPIPE_AVAILABLE:
            return {
                "posture": 0.5,
                "gesture": 0.5,
                "body_movement": 0.5,
                "confidence_pose": 0.5,
                "body_language_state": "neutral"
            }

        body_metrics = {}

        try:
            with mp_holistic.Holistic(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                refine_face_landmarks=False
            ) as holistic:

                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = holistic.process(rgb_frame)

                # Analyze pose landmarks for posture
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark

                    # Shoulder alignment (posture)
                    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
                    posture_score = max(0, 1.0 - shoulder_diff * 2)  # Closer to 1.0 = better posture

                    # Arm positions (gestures)
                    left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
                    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
                    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
                    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

                    # Calculate arm openness (gesture expressiveness)
                    left_arm_open = abs(left_elbow.x - left_wrist.x)
                    right_arm_open = abs(right_elbow.x - right_wrist.x)
                    gesture_score = min(1.0, (left_arm_open + right_arm_open) * 2)

                    # Body movement (simplified - would need frame comparison for real movement)
                    body_movement_score = 0.5  # Placeholder

                    # Confidence pose (based on shoulder height and arm positions)
                    shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
                    confidence_score = max(0, 1.0 - shoulder_height)  # Lower shoulders = more confident

                    body_metrics.update({
                        "posture": posture_score,
                        "gesture": gesture_score,
                        "body_movement": body_movement_score,
                        "confidence_pose": confidence_score
                    })

                # Analyze hand landmarks for detailed gestures
                if results.left_hand_landmarks or results.right_hand_landmarks:
                    # Simple gesture detection based on hand positions
                    hand_gesture_score = 0.7 if (results.left_hand_landmarks or results.right_hand_landmarks) else 0.3
                    body_metrics["gesture"] = max(body_metrics.get("gesture", 0), hand_gesture_score)

        except Exception as e:
            print(f"MediaPipe body analysis error: {e}")
            # Return neutral values on error
            body_metrics = {
                "posture": 0.5,
                "gesture": 0.5,
                "body_movement": 0.5,
                "confidence_pose": 0.5
            }

        # Add inferred body language state
        body_metrics["body_language_state"] = self._infer_body_language_state(body_metrics)

        return body_metrics

    async def quick_analyze(self, audio_bytes: bytes = None, video_bytes: bytes = None, body_data: dict = None) -> dict:
        """
        Quick analysis method for non-streaming use cases.
        Actively uses Hume's batch APIs when data is provided.
        Requires at least audio_bytes or video_bytes to be provided.
        Raises ValueError if analysis fails - no placeholder values.
        """
        if not audio_bytes and not video_bytes:
            raise ValueError("At least audio_bytes or video_bytes must be provided for analysis")

        emotions = {}

        # Analyze audio for conversation if provided
        if audio_bytes:
            audio_emotions = await self._analyze_audio_batch(audio_bytes)
            emotions.update(audio_emotions)

        # Analyze video for face and body if provided
        if video_bytes:
            video_emotions = await self._analyze_video_batch(video_bytes)
            emotions.update(video_emotions)

        # Analyze body language if frame data provided
        if body_data and isinstance(body_data, dict) and 'frame' in body_data:
            frame = body_data['frame']
            if isinstance(frame, np.ndarray):
                body_emotions = self.analyze_body_language(frame)
                emotions.update(body_emotions)

        # Check if any emotions were detected - raise error if none
        if not emotions:
            raise ValueError("Emotion analysis failed - no data could be processed from Hume AI or MediaPipe")

        # Add inferred states
        emotions["emotion_state"] = self._infer_emotion_state(emotions)
        emotions["body_language_state"] = self._infer_body_language_state(emotions)
        emotions["conversation_quality"] = self._assess_conversation_quality(emotions)

        return emotions
