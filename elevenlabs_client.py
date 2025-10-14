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
            return b""  # Return empty bytes on error
