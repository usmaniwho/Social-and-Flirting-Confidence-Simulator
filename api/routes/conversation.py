# voice_call_router.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import base64
import io
import asyncio
import json
from datetime import datetime
from ai_personality import GPTClient
from elevenlabs_client import ElevenLabsClient
from core.session_store import session_store
from core.data_contract import Personality
from openai import AsyncOpenAI

router = APIRouter()

# ✅ Use async OpenAI client (fixes blocking issue)
openai_client = AsyncOpenAI()


@router.websocket("/realtime/voice-stream")
async def voice_call(websocket: WebSocket):
    """
    Real-time bidirectional voice call endpoint.
    - Receives user audio chunks (base64).
    - Converts to text via STT (Whisper).
    - Sends text to GPT and gets personality-matched response.
    - Converts GPT response to voice via ElevenLabs.
    - Sends back both text + voice (base64).
    - Keeps conversation history in session store.
    """

    await websocket.accept()
    gpt_client = GPTClient()
    elevenlabs_client = ElevenLabsClient()

    print("🎙️ Voice call started")

    try:
        while True:
            # Receive JSON payload from frontend
            data = await websocket.receive_json()
            session_id = data.get("session_id")
            audio_b64 = data.get("audio")

            if not session_id or not audio_b64:
                await websocket.send_json({"error": "Missing session_id or audio"})
                continue

            # ✅ Get or create session safely
            session = session_store.get_session(session_id)
            if not session:
                # --- FIX: session_store.save_session() requires user_id, mode, etc.
                session = {
                    "user_id": "anonymous",
                    "mode": "voice_call",
                    "scenario": "default",
                    "personality": Personality.CALM.value,
                    "objectives": [],
                    "started_at": datetime.utcnow(),
                    "conversation_history": []
                }
                session_store.save_session(session_id, session)

            # ✅ Ensure correct Enum mapping
            personality = Personality(session.get("personality", Personality.CALM.value))
            conversation_history = session.get("conversation_history", [])

            # Step 1️⃣: Decode incoming audio
            user_audio_bytes = base64.b64decode(audio_b64)

            # Step 2️⃣: Transcribe using Whisper (async)
            user_text = await transcribe_audio(user_audio_bytes)
            print(f"🗣️ User said: {user_text}")

            # Step 3️⃣: Generate GPT reply (personality-matched)
            gpt_reply = await gpt_client.generate_response(
                user_text, personality, conversation_history
            )
            print(f"🤖 GPT replied: {gpt_reply}")

            # Step 4️⃣: Convert GPT text → speech using ElevenLabs
            reply_audio_bytes = await elevenlabs_client.generate_speech(
                gpt_reply, personality
            )

            reply_audio_b64 = base64.b64encode(reply_audio_bytes).decode("utf-8")

            # Step 5️⃣: Update conversation history (not yet in DB schema)
            conversation_history += [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": gpt_reply}
            ]
            session["conversation_history"] = conversation_history[-20:]

            # ✅ Save updated session
            session_store.save_session(session_id, session)

            # Log stream chunks for transcript
            try:
                session_store.add_stream_chunk(session_id, speaker="user", text_chunk=user_text)
                session_store.add_stream_chunk(session_id, speaker="ai", text_chunk=gpt_reply)
            except Exception as e:
                print(f"SessionStore stream log error: {e}")

            # Step 6️⃣: Send back both transcript + AI audio
            await websocket.send_json({
                "user_text": user_text,
                "reply_text": gpt_reply,
                "reply_audio": reply_audio_b64
            })

    except WebSocketDisconnect:
        print("❌ Voice call ended")

    except Exception as e:
        # ✅ More structured error handling
        await websocket.send_json({
            "type": "error",
            "message": f"Voice call failed: {str(e)}"
        })
        print(f"❌ Error in voice call: {e}")


# --------------------------
# 🎧 ASYNC SPEECH-TO-TEXT HELPER
# --------------------------
async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Convert incoming voice bytes to text using OpenAI Whisper (async).
    Uses in-memory buffer to avoid temp file collisions.
    """
    try:
        # ✅ Use in-memory stream instead of temp files
        audio_file = io.BytesIO(audio_bytes)

        # ✅ Use async Whisper endpoint with proper file format specification
        transcription = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio_file, "audio/webm")
        )
        return transcription.text.strip()

    except Exception as e:
        print(f"⚠️ STT Error: {e}")
        return "[Could not transcribe audio]"
