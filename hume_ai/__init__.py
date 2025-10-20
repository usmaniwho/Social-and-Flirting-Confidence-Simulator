# hume_ai/__init__.py
from .hume_ai_client import HumeStreamClient

# Export the class for per-connection instantiation
__all__ = ["HumeStreamClient"]

# Optional convenience analyze wrapper (for non-streaming use)
async def analyze(audio_bytes, body_data):
    """
    Simple wrapper: send audio & body to Hume and wait for quick response.
    Implementation detail depends on Hume SDK behavior.
    """
    # If your client exposes send_* and receive_loop with callback, you can make a simple
    # fire-and-listen approach here — for now, just call methods if implemented.
    client = HumeStreamClient()
    return await client.quick_analyze(audio_bytes, body_data)
