from core.data_contract import Personality
from openai import AsyncOpenAI
import base64
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()

class GPTClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OpenAI API key not available. Using fallback responses.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)

    async def generate_response(self, user_text: str, personality: Personality, history: list):
        """Generate GPT reply with emotional expression matching personality."""

        print(f"Mock: Generating GPT response for user text: '{user_text}' with personality: {personality}")

        # Mock responses based on personality
        mock_responses = {
            Personality.PLAYFUL: [
                "Wow, that's so cool! 😊 Tell me more about it!",
                "Haha, I love hearing about that! What happened next?",
                "That's awesome! You must be so excited about it!"
            ],
            Personality.CALM: [
                "I understand. That sounds quite meaningful to you.",
                "Thank you for sharing that. How are you feeling about it now?",
                "I see. That's an interesting perspective."
            ],
            Personality.SHY: [
                "Oh... that's nice. Um, could you tell me more?",
                "I see... that sounds important. How do you feel?",
                "Thanks for sharing... I appreciate you telling me that."
            ]
        }

        import random
        responses = mock_responses.get(personality, ["That's interesting. Tell me more."])
        mock_response = random.choice(responses)
        print(f"Mock GPT response: '{mock_response}'")
        return mock_response

    # 🔹 ADDED: method to process emotion input and adjust GPT response dynamically
    async def generate_emotionally_adaptive_response(self, user_text: str, personality: Personality, emotion_state: str, history: list):
        """
        Added method for emotional adaptation.
        Adjusts GPT tone based on live emotion feedback (from Hume stream).
        Example: If user sounds 'stressed', GPT responds more soothingly.
        """
        emotion_context = {
            "happy": "The user seems happy — match their cheerful tone with warm and positive energy.",
            "focused": "The user seems focused — keep your tone confident and clear.",
            "disengaged": "The user sounds disengaged — speak gently and try to re-engage with empathy.",
            "excited": "The user sounds excited — reply with energy and enthusiasm.",
            "stressed": "The user sounds stressed — calm them down with a relaxed and reassuring tone.",
            "neutral": "Keep a balanced, natural tone.",
        }.get(emotion_state, "Speak naturally and empathetically.")

        # 🔹 Add emotional context before generation
        history = history + [{"role": "system", "content": f"Emotion context: {emotion_context}"}]
        return await self.generate_response(user_text, personality, history)

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes using OpenAI Whisper API.
        Uses mock transcription for demonstration.
        """
        print(f"Mock: Transcribing {len(audio_bytes)} bytes of audio")
        # Mock transcription - return a sample text
        mock_transcripts = [
            "Hello, how are you today?",
            "I'm feeling a bit nervous about this conversation.",
            "That's really interesting! Tell me more.",
            "I had a great day at work today.",
            "Can you help me with something?"
        ]
        import random
        mock_transcript = random.choice(mock_transcripts)
        print(f"Mock transcription: '{mock_transcript}'")
        return mock_transcript
