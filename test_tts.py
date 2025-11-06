import asyncio
from elevenlabs_client import ElevenLabsClient
from core.data_contract import Personality

async def test_tts():
    client = ElevenLabsClient()
    audio = await client.generate_speech('Hello, this is a test.', Personality.CALM)
    print(f'Audio generated: {len(audio)} bytes')

if __name__ == "__main__":
    asyncio.run(test_tts())
