import os
import asyncio
import json
from hume import AsyncHumeClient
from hume.expression_measurement.stream import Config as EmConfig
from hume.expression_measurement.stream.socket_client import StreamConnectOptions
from hume.expression_measurement.stream import StreamFace, StreamLanguage

from dotenv import load_dotenv
load_dotenv()

class HumeStreamClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("HUME_API_KEY")
        if not self.api_key:
            raise ValueError("HUME_API_KEY environment variable not set")
        print(f"HumeStreamClient initialized with API key")
        self.client = AsyncHumeClient(api_key=self.api_key)
        # configure streaming models (face + language for speech)
        self.config = EmConfig(face=StreamFace(), language=StreamLanguage())

    async def connect(self):
        options = StreamConnectOptions(config=self.config)
        self.stream_cm = self.client.expression_measurement.stream.connect(options=options)
        return self.stream_cm

    async def disconnect(self):
        # No need to close since we use context manager
        pass

    async def receive_loop(self, on_emotion_callback):
        """
        Keep receiving streaming messages. Call the on_emotion_callback with a dict:
          { 'eye_contact': ..., 'smile': ..., 'vocal_tone': ..., 'pacing': ..., 'engagement': ... }
        """
        async with self.stream_cm as socket:
            async for msg in socket:
                # msg will include face and speech predictions
                face_pred = msg.face.predictions if msg.face else []
                speech_pred = msg.speech.predictions if msg.speech else []
                # parse top-level metrics (map from Hume model output)
                val = {
                    "eye_contact": self._map_face_score(face_pred, "EyeContact"),
                    "smile": self._map_face_score(face_pred, "Smile"),
                    "vocal_tone": self._map_speech_score(speech_pred, "VocalTone"),
                    "pacing": self._map_speech_score(speech_pred, "Pacing"),
                    "engagement": self._map_speech_score(speech_pred, "Engagement"),
                }
                on_emotion_callback(val)

    def _map_face_score(self, predictions, target_name):
        # find the prediction with name == target_name, else 0
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    def _map_speech_score(self, predictions, target_name):
        for p in predictions:
            if p.name == target_name:
                return p.score
        return 0.0

    async def send_webcam_data(self, webcam_data: bytes):
        """
        Send webcam data to Hume for analysis.
        """
        async with self.stream_cm as socket:
            await socket.send_face(webcam_data)

    async def send_mic_data(self, mic_data: bytes):
        """
        Send microphone data to Hume for analysis.
        """
        async with self.stream_cm as socket:
            await socket.send_audio(mic_data)
