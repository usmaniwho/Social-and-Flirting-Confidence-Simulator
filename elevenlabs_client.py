import os
import elevenlabs
from core.data_contract import Personality
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        elevenlabs.set_api_key(self.api_key)

    def get_voice_for_personality(self, personality: Personality) -> str:
        """Get the voice ID for a specific personality."""
        voice_map = {
            Personality.PLAYFUL: "21m00Tcm4TlvDq8ikWAM",  # Rachel (playful, energetic)
            Personality.CALM: "AZnzlk1XvdvUeBnXmlld",    # Domi (calm, soothing)
            Personality.SHY: "EXAVITQu4vr4xnSDxMaL"      # Bella (soft, reserved)
        }
        return voice_map.get(personality, voice_map[Personality.CALM])

    # 🔹 ADDED: Function to enrich text tone and add cues
    def style_text_for_personality(self, text: str, personality: Personality) -> str:
        """
        Adjusts tone or adds emotional cues to the GPT text
        based on the selected personality.
        """
        if personality == Personality.PLAYFUL:
            styled = f"(cheerfully) {text} 😊"
        elif personality == Personality.CALM:
            styled = f"(softly, calm tone) {text}"
        elif personality == Personality.SHY:
            styled = f"(hesitantly, gentle tone) {text}..."
        else:
            styled = text
        return styled

    def get_voice_settings_for_personality(self, personality: Personality) -> dict:
        """
        Returns ElevenLabs voice settings for controlling emotion and style.
        """
        if personality == Personality.PLAYFUL:
            return {"stability": 0.25, "similarity_boost": 0.8, "style": 0.7, "use_speaker_boost": True}
        elif personality == Personality.CALM:
            return {"stability": 0.8, "similarity_boost": 0.6, "style": 0.3, "use_speaker_boost": True}
        elif personality == Personality.SHY:
            return {"stability": 0.9, "similarity_boost": 0.4, "style": 0.2, "use_speaker_boost": False}
        return {"stability": 0.5, "similarity_boost": 0.5}

    async def generate_speech(self, text: str, personality: Personality) -> bytes:
        """Generate speech audio for the given text using the personality's voice."""
        voice_id = self.get_voice_for_personality(personality)
        try:
            audio = elevenlabs.generate(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )
            # Assuming audio is bytes; adjust if ElevenLabs returns a different format
            return audio
        except Exception as e:
            print(f"Error generating speech: {e}")
            # Return empty bytes on error to prevent crashes
            return b""

    # 🔹 ADDED: Optional real-time stream generator (for WebSocket chunk sending)
    async def stream_speech_chunks(self, text: str, personality: Personality):
        """
        Added method for real-time streaming to frontend.
        Yields small audio chunks instead of one big file.
        Useful for live /voice-stream responses.
        """
        try:
            voice_id = self.get_voice_for_personality(personality)
            stream = elevenlabs.stream(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )
            async for chunk in stream:
                yield chunk  # send chunk to WebSocket in real-time
        except Exception as e:
            print(f"Error streaming ElevenLabs audio: {e}")
            return
