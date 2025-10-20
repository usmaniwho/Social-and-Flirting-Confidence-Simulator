from core.data_contract import Personality
from openai import AsyncOpenAI
import base64
import tempfile
import os

class GPTClient:
    def __init__(self):
        self.client = AsyncOpenAI()

    async def generate_response(self, user_text: str, personality: Personality, history: list):
        """Generate GPT reply with emotional expression matching personality."""
        
        # Define personality prompt
        personality_prompts = {
            Personality.CALM: (
                "You are calm, composed, and soothing. "
                "You reply with empathy, patience, and warmth. "
                "Keep your tone slow, balanced, and reassuring. "
                "Express calm emotions subtly but clearly."
            ),
            Personality.SHY: (
                "You are shy, gentle, and soft-spoken. "
                "You reply politely and with small hesitations or short pauses. "
                "Express emotions quietly, as if you're slightly nervous but kind."
            ),
            Personality.PLAYFUL: (
                "You are playful, expressive, and full of energy. "
                "You speak with enthusiasm and emotion, using fun phrases or light humor. "
                "Express excitement and positivity vividly."
            )
        }

        system_message = {
            "role": "system",
            "content": (
                f"You are an emotional AI voice companion. {personality_prompts.get(personality)} "
                "Always speak naturally as if you are talking in a real voice call."
            ),
        }

        messages = [system_message] + history[-10:] + [{"role": "user", "content": user_text}]

        completion = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.9,  # higher temperature = more personality variation
            max_tokens=250
        )

        return completion.choices[0].message.content.strip()

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
        """
        try:
            # Save audio bytes to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            # Open the file for transcription
            with open(temp_file_path, 'rb') as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

            # Clean up the temporary file
            os.unlink(temp_file_path)

            return transcript.strip()

        except Exception as e:
            print(f"Audio transcription error: {e}")
            return "[Audio transcription failed]"
