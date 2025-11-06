import asyncio
from ai_personality.gpt_client import GPTClient
from core.data_contract import Personality

async def test_gpt():
    client = GPTClient()
    response = await client.generate_response('Hello', Personality.CALM, [])
    print(f'GPT response: {response}')

if __name__ == "__main__":
    asyncio.run(test_gpt())
