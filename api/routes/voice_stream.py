
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import base64
import json
import asyncio
from core.session_store import session_store
from core.data_contract import Personality
from ai_personality import GPTClient
from elevenlabs_client import ElevenLabsClient
from core.scoring import FRSComputation
from hume_ai import HumeStreamClient

router = APIRouter()

# Accumulated frs (keeps updates until /session/end is called)
accumulated_frs = {}

gpt_client = GPTClient()
tts_client = ElevenLabsClient()
frs_engine = FRSComputation()

@router.websocket("/voice-stream")
async def voice_stream(websocket: WebSocket):
    """
    Realtime multimodal voice stream:
      - receives JSON with keys: session_id, audio (base64), optional body (json)
      - transcribes audio (STT) on server or receives frontend transcript
      - calls Hume analyze(...) to obtain emotions
      - calls GPT with emotion-aware prompt
      - calls ElevenLabs to generate audio
      - returns { response, audio, emotions, frs_update } back to frontend
    """
    await websocket.accept()

    # Instantiate HumeStreamClient per connection
    hume_client = HumeStreamClient()
    await hume_client.connect()

    # Shared variable for latest emotions
    latest_emotions = {
        "eye_contact": 0.0, "smile": 0.0, "vocal_tone": 0.0,
        "pacing": 0.0, "engagement": 0.0, "emotion_state": "neutral"
    }

    # Callback to update latest emotions
    def on_emotion_callback(emotions):
        nonlocal latest_emotions
        latest_emotions = emotions

    # Start receive_loop in background task
    receive_task = asyncio.create_task(hume_client.receive_loop(on_emotion_callback))

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)

            session_id = payload.get("session_id")
            if not session_id:
                await websocket.send_json({"error": "Missing session_id"})
                continue

            # Check if session is ended
            session = session_store.get_session(session_id)
            if session and session.get("ended"):
                print(f"Session {session_id} has ended, closing WebSocket")
                await websocket.send_json({"error": "Session has ended"})
                await websocket.close()
                return

            # Skip processing if session is ended (additional check)
            if session and session.get("ended"):
                continue

            # audio: base64 encoded bytes from frontend
            audio_b64 = payload.get("audio")
            body_data = payload.get("body")  # optional pose/landmarks

            # If frontend sent a transcript (quick path), accept it else server should transcribe
            transcript = payload.get("transcript")

            # Ensure session exists, if not create default "First Date Jitters" session
            if not session:
                # create minimal session meta (safe for session_store.save_session)
                session = {
                    "user_id": "anonymous",
                    "mode": "romantic",
                    "scenario": "first_date_jitters",
                    "personality": Personality.CALM.value,
                    "objectives": {
                        "main": "Deepen conversation",
                        "bonus": ["Eye contact", "Anecdote", "Reciprocity"],
                        "medal_conditions": ["Charisma", "Friendliness", "Composure"]
                    },
                    "prompt": "You're on your first date and feeling a bit nervous. The conversation needs to flow naturally.",
                    "started_at": __import__("datetime").datetime.utcnow(),
                    "conversation_history": []
                }
                session_store.save_session(session_id, session)

            personality = Personality(session.get("personality", Personality.CALM.value))

            # 1) prepare audio bytes if provided
            audio_bytes = None
            if audio_b64:
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception:
                    audio_bytes = None

            # 2) Send audio data to Hume stream if available
            if audio_bytes:
                try:
                    await hume_client.send_mic_data(audio_bytes)
                except Exception as e:
                    print(f"Error sending audio to Hume: {e}")

            # 3) Use latest emotions from streaming callback
            emotions = latest_emotions.copy()

            # 3) If transcript missing, use OpenAI Whisper to transcribe the audio
            if not transcript and audio_bytes:
                try:
                    transcript = await gpt_client.transcribe_audio(audio_bytes)
                except Exception as e:
                    print(f"Transcription error: {e}")
                    transcript = payload.get("fallback_text", "[audio received]")

            # 4) Generate GPT reply adapted to user's emotion state
            try:
                ai_response = await gpt_client.generate_emotionally_adaptive_response(
                    user_text=transcript,
                    personality=personality,
                    emotion_state=emotions.get("emotion_state", "neutral"),
                    history=session.get("conversation_history", [])
                )
            except Exception as e:
                print(f"GPT error: {e}")
                ai_response = "Sorry, I couldn't process that. Could you say it again?"

            # 5) Style text for TTS using ElevenLabs helper (keeps existing logic intact)
            styled_text = tts_client.style_text_for_personality(ai_response, personality)

            # 6) Generate speech bytes (non-streaming for now) - you can switch to stream_speech_chunks() later
            try:
                tts_bytes = await tts_client.generate_speech(styled_text, personality)
            except Exception as e:
                print(f"TTS error: {e}")
                tts_bytes = b""

            tts_b64 = base64.b64encode(tts_bytes).decode("utf-8") if tts_bytes else ""

            # 7) Update conversation history & store transcript + emotion chunk
            conv = session.get("conversation_history", [])
            conv.append({"role": "user", "content": transcript})
            conv.append({"role": "assistant", "content": ai_response})
            session["conversation_history"] = conv[-20:]
            session_store.save_session(session_id, session)

            # Log stream chunks for transcript + emotion so we can summarize later
            try:
                session_store.add_stream_chunk(session_id, speaker="user", text_chunk=transcript, emotion_state=emotions.get("emotion_state"))
                session_store.add_stream_chunk(session_id, speaker="ai", text_chunk=ai_response, emotion_state=None)
            except Exception as e:
                print(f"SessionStore stream log error: {e}")

            # 8) Compute FRS update from emotions
            frs_update = frs_engine.update_metrics(session_id, emotions)
            accumulated_frs.setdefault(session_id, []).append(frs_update)

            # 9) Send response back to frontend
            await websocket.send_json({
                "response": ai_response,
                "audio": tts_b64,
                "emotions": emotions,
                "frs_update": frs_update
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        # ensure errors are visible but keep connection handling stable
        print(f"voice_stream fatal error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
        await websocket.close()
    finally:
        # Ensure proper disconnection
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        await hume_client.disconnect()
