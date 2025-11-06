# conversation.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.session_store import session_store

router = APIRouter()

class SendMessageRequest(BaseModel):
    session_id: str
    message: str

@router.post("/send")
def send_message(request: SendMessageRequest):
    """
    Send a message in a conversation session.
    """
    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Add user message to conversation history
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    session['conversation_history'].append({"role": "user", "content": request.message})

    # For now, just store the message. AI response will be handled via WebSocket
    session_store.save_session(request.session_id, session)

    return {"status": "Message sent"}

@router.get("/conversation/history/{session_id}")
def get_conversation_history(session_id: str):
    """
    Get conversation history for a session.
    """
    session = session_store.get_session(session_id)
    if not session:
        return {"messages": []}  # Return empty list if session not found

    history = session.get('conversation_history', [])
    return {"messages": history}

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

            # Step 2️⃣: Transcribe via Whisper
            user_text = await transcribe_audio(user_audio_bytes)
            print(f"🗣️ User said: {user_text}")

            # ✅ Skip GPT call if transcription failed
            if not user_text or user_text.strip() in ["", "[Could not transcribe audio]"]:
                await websocket.send_json({
                    "error": "Speech could not be transcribed properly. Please try again."
                })
                continue

            # Step 3️⃣: Generate GPT reply
            try:
                # ✅ Ensure GPTClient internally uses AsyncOpenAI and formats messages=[...]
                gpt_reply = await gpt_client.generate_response(
                    user_text, personality, conversation_history
                )

                # ✅ Handle null or empty replies safely
                if not gpt_reply or not gpt_reply.strip():
                    gpt_reply = "I'm here, but I couldn't understand that clearly."

                print(f"🤖 GPT replied: {gpt_reply}")

            except Exception as gpt_error:
                print(f"❌ GPT generation failed: {gpt_error}")
                gpt_reply = "Sorry, I couldn't generate a response right now."
                await websocket.send_json({"error": f"GPT failed: {str(gpt_error)}"})
                continue

            # Step 4️⃣: Convert GPT text → speech using ElevenLabs
            try:
                reply_audio_bytes = await elevenlabs_client.generate_speech(
                    gpt_reply, personality
                )
                reply_audio_b64 = base64.b64encode(reply_audio_bytes).decode("utf-8")
            except Exception as tts_error:
                print(f"❌ TTS generation failed: {tts_error}")
                reply_audio_b64 = None
                await websocket.send_json({"error": f"TTS failed: {str(tts_error)}"})
                # Continue without audio

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
            response_data = {
                "user_text": user_text,
                "reply_text": gpt_reply
            }
            if reply_audio_b64:
                response_data["reply_audio"] = reply_audio_b64
            await websocket.send_json(response_data)

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
    Handles both WAV and WebM formats.
    """
    try:
        from pydub import AudioSegment

        audio_buffer = io.BytesIO(audio_bytes)

        # Try to load as WAV, fallback to WebM
        try:
            audio_segment = AudioSegment.from_wav(audio_buffer)
        except Exception:
            audio_buffer.seek(0)
            audio_segment = AudioSegment.from_file(audio_buffer, format="webm")

        # Export clean WAV for Whisper API
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        # ✅ Use async Whisper transcription endpoint
        transcription = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_buffer
        )

        # ✅ Return cleaned text
        text = transcription.text.strip() if transcription and transcription.text else ""
        return text or "[Could not transcribe audio]"

    except Exception as e:
        print(f"⚠️ STT Error: {e}")
        return "[Could not transcribe audio]"
