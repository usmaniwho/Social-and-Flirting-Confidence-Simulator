
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import base64
import json
from core.session_store import session_store
from core.data_contract import Personality
from ai_personality.gpt_client import GPTClient
from elevenlabs_client import ElevenLabsClient
from core.scoring import FRSComputation
from hume_ai.hume_ai_client import HumeStreamClient

router = APIRouter()

# Accumulated frs (keeps updates until /session/end is called)
accumulated_frs = {}

gpt_client = GPTClient()
tts_client = ElevenLabsClient()
frs_engine = FRSComputation()
hume_client = HumeStreamClient()

@router.websocket("/voice-stream")
async def voice_stream(websocket: WebSocket):
    """
    Realtime voice stream:
      - receives JSON with keys: session_id, audio (base64)
      - transcribes audio (STT)
      - calls GPT
      - calls ElevenLabs to generate audio
      - returns { reply_text, reply_audio, user_text, emotions, frs_update } back to frontend
    """
    print("Voice WebSocket accepted")
    await websocket.accept()

    # Default emotions (no Hume for now)
    emotions = {
        "eye_contact": 0.5, "smile": 0.5, "vocal_tone": 0.5,
        "pacing": 0.5, "engagement": 0.5, "emotion_state": "neutral"
    }

    try:
        while True:
            print("Waiting for message")
            raw = await websocket.receive_text()
            print(f"Received raw: {raw[:100]}...")
            payload = json.loads(raw)
            print(f"Parsed payload: session_id={payload.get('session_id')}, audio_len={len(payload.get('audio', ''))}")

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

            # audio: base64 encoded bytes from frontend
            audio_b64 = payload.get("audio")

            # If frontend sent a transcript, accept it else transcribe
            transcript = payload.get("transcript")

            # Ensure session exists
            if not session:
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

            # Transcribe if needed (convert webm to wav for Whisper compatibility)
            transcript_display = None
            input_text = transcript or ""
            if not transcript and audio_b64:
                try:
                    import io
                    from pydub import AudioSegment
                    audio_bytes = base64.b64decode(audio_b64)
                    print(f"Audio bytes len: {len(audio_bytes)}")

                    # Convert webm to wav using pydub
                    webm_audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
                    wav_buffer = io.BytesIO()
                    webm_audio.export(wav_buffer, format="wav")
                    wav_buffer.seek(0)
                    setattr(wav_buffer, "name", "audio.wav")

                    transcript = await gpt_client.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=wav_buffer,
                        response_format="text"
                    )
                    transcript = transcript.strip()
                    transcript_display = transcript
                    input_text = transcript
                    print(f"Transcribed: '{transcript}'")
                except Exception as e:
                    print(f"Transcription error: {e}")
                    import traceback
                    traceback.print_exc()
                    # Do not feed the error to GPT; proceed with empty input
                    transcript_display = f"[Transcription failed: {str(e)}]"
                    input_text = ""

            if not input_text:
                # If still nothing, keep empty input but show placeholder to user
                transcript_display = transcript_display or "[no audio]"

            # Analyze emotions from audio using Hume AI
            if audio_b64 and input_text:
                try:
                    audio_emotions = await hume_client.quick_analyze(audio_bytes=audio_bytes)
                    emotions.update(audio_emotions)
                    print(f"Emotion analysis: {emotions.get('emotion_state', 'neutral')}")
                except Exception as e:
                    print(f"Hume AI emotion analysis failed: {e}")
                    # Keep default emotions

            # Generate GPT response with streaming
            try:
                full_response = ""
                frs_update = {}  # ✅ Define before usage

                async for chunk in gpt_client.generate_streaming_response(
                    user_text=input_text,
                    personality=personality,
                    emotion_state=emotions.get("emotion_state", "neutral"),
                    history=session.get("conversation_history", [])
                ):
                    full_response += chunk
                    # Send partial text to frontend for real-time display
                    await websocket.send_json({
                        "partial_text": chunk,
                        "user_text": transcript_display,
                        "emotions": emotions,
                        "frs_update": frs_update
                    })

                ai_response = full_response.strip()
                if not ai_response:
                    ai_response = "I'm here — could you say that again?"
                print(f"GPT response: {ai_response[:80]}...")

            except Exception as e:
                print(f"GPT error: {e}")
                ai_response = "Sorry, I couldn’t process that right now."

            # Generate TTS with streaming
            try:
                # Estimate cost before generating
                estimated_cost = tts_client.estimate_cost(ai_response)
                print(f"Estimated TTS cost: {estimated_cost} credits for {len(ai_response)} characters")

                # Check if we have enough credits (assuming 40000 is the quota)
                if estimated_cost > 106:  # From the error, had 106 remaining
                    print(f"Insufficient credits: need {estimated_cost}, have ~106")
                    await websocket.send_json({
                        "error": f"Insufficient ElevenLabs credits. Need {estimated_cost}, have ~106 remaining."
                    })
                    tts_b64 = ""
                else:
                    async for audio_chunk in tts_client.stream_speech_chunks(ai_response, personality):
                        # Send audio chunks to frontend for real-time playback
                        audio_b64 = base64.b64encode(audio_chunk).decode("utf-8")
                        await websocket.send_json({
                            "audio_chunk": audio_b64,
                            "user_text": transcript,
                            "emotions": emotions,
                            "frs_update": frs_update
                        })
                    tts_b64 = ""  # No full audio since streaming
                    print("TTS streamed successfully")
            except Exception as e:
                print(f"TTS error: {e}")
                tts_b64 = ""

            # Update conversation history
            conv = session.get("conversation_history", [])
            conv.append({"role": "user", "content": input_text or "[voice]"})
            conv.append({"role": "assistant", "content": ai_response})
            session["conversation_history"] = conv[-20:]
            session_store.save_session(session_id, session)

            # Store transcript
            try:
                session_store.add_stream_chunk(session_id, speaker="user", text_chunk=transcript, emotion_state="neutral")
                session_store.add_stream_chunk(session_id, speaker="ai", text_chunk=ai_response, emotion_state=None)
            except Exception as e:
                print(f"SessionStore error: {e}")

            # Compute FRS
            frs_update = frs_engine.update_metrics(session_id, emotions)
            accumulated_frs.setdefault(session_id, []).append(frs_update)

            # Send response
            print("Sending response")
            await websocket.send_json({
                "reply_text": ai_response,
                "reply_audio": tts_b64,
                "user_text": transcript_display,
                "emotions": emotions,
                "frs_update": frs_update
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Voice stream error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
        await websocket.close()
