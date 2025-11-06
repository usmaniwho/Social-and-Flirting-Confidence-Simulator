#session.py
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from models.models import SessionCreate, SessionSummary, FRSResult, ScenarioObjective, Mode
from datetime import datetime
import uuid
import json
import base64
from core import session_store
from hume_ai import analyze  # Use the analyze function from hume_ai/__init__.py
from elevenlabs_client import ElevenLabsClient
from core.data_contract import Personality

router = APIRouter()

# Expanded scenario definitions with modes
scenarios = {
    "social": {
        "house_party": {
            "objective": ScenarioObjective(
                main="Join conversation naturally",
                bonus=["Eye contact", "Smile", "Initiate contact"],
                medal_conditions=["Friendliness", "Composure", "Adaptability"],
                dynamic_objectives=["Make a new friend", "Build trust quickly"]
            ),
            "prompt": "You're at a house party and notice a group of people having an interesting conversation. You decide to join in."
        },
        "work_mixer": {
            "objective": ScenarioObjective(
                main="Navigate casual group dynamics",
                bonus=["Listen first", "Contribute usefully", "Include others"],
                medal_conditions=["Friendliness", "Awareness", "Composure"],
                dynamic_objectives=["Get invited to an event", "Establish common ground"]
            ),
            "prompt": "You're at a work networking mixer and spot someone from another department you'd like to connect with."
        },
        "group_conversation": {
            "objective": ScenarioObjective(
                main="Participate effectively in group setting",
                bonus=["Listen first", "Contribute usefully", "Include others"],
                medal_conditions=["Friendliness", "Composure", "Awareness"],
                dynamic_objectives=["Make a new friend", "Build trust quickly"]
            ),
            "prompt": "You're in a group conversation at a social gathering and want to contribute meaningfully."
        }
    },
    "romantic": {
        "bar_encounter": {
            "objective": ScenarioObjective(
                main="Start a conversation and keep it flowing",
                bonus=["Make an observational joke", "Maintain eye contact", "Use subtle flattery"],
                medal_conditions=["Charisma", "Friendliness", "Persuasion"],
                dynamic_objectives=["Ask someone out", "Build attraction", "Escalate connection"]
            ),
            "prompt": "You're at a bar and see someone attractive across the room. You decide to approach them."
        },
        "first_date_jitters": {
            "objective": ScenarioObjective(
                main="Deepen the connection by asking engaging, non-generic questions that touch on passions, values, or dreams",
                bonus=["Maintain natural eye contact", "Share a short, relevant personal anecdote", "Show reciprocity and balance in conversation"],
                medal_conditions=["Charisma", "Friendliness", "Composure", "Compassion"],
                dynamic_objectives=["Build trust quickly", "Respond well to awkward silence"]
            ),
            "prompt": "Imagine this: you're sitting at a cozy café, the soft hum of conversation and the aroma of coffee filling the air. Opposite you, on your video call screen, is Alex, your date. You've exchanged pleasantries – the standard 'How was your day?' and 'What do you do?' – but now there's a slight, almost imperceptible lull. It's that moment where the conversation could either fizzle into polite silence or spark into something genuinely engaging. Alex's expression is open, a slight smile on their lips, waiting. You see yourself in the small frame, and the microphone icon softly glows, signaling it's your turn. Your main goal in this scenario is to deepen the connection. This isn't about rapid-fire questions or dominating the conversation. It's about finding that natural pivot point to explore something more personal, something that truly reveals who Alex is, or who you are. You need to ask an engaging, non-generic question that touches on their passions, values, or dreams. While you're striving for that deeper connection, also remember to smoothly share a short, relevant personal anecdote. This shows you're not just interrogating them, but you're also willing to open up yourself, creating a comfortable space for reciprocity."
        },
        "coffee_shop_approach": {
            "objective": ScenarioObjective(
                main="Break the ice and have meaningful interaction",
                bonus=["Tease respectfully", "Listen actively", "Respond smoothly"],
                medal_conditions=["Charisma", "Friendliness", "Awareness"],
                dynamic_objectives=["Leave with verbal agreement to meet again", "Establish common ground"]
            ),
            "prompt": "You're in a coffee shop and notice someone reading an interesting book. You want to start a conversation."
        }
    }
}

@router.post("/start")
async def start_session(payload: SessionCreate):
    """
    Start a new session with the given parameters.
    Temporarily relaxed calibration requirement for testing - only requires 1 step.
    """
    # Temporarily relaxed calibration check - require at least 1 step for testing
    from api.routes.frs import calibration_data, calibration_steps
    user_cal_data = calibration_data.get(payload.user_id)
    min_required_steps = 1  # Temporarily set to 1 for testing
    calibration_done = user_cal_data and len(user_cal_data.steps_completed) >= min_required_steps

    if not calibration_done:
        print(f"Warning: User {payload.user_id} has completed {len(user_cal_data.steps_completed) if user_cal_data else 0} calibration steps. Minimum required: {min_required_steps}. Allowing session to start for testing.")

    session_id = str(uuid.uuid4())
    mode_scenarios = scenarios.get(payload.mode, {})
    scenario_data = mode_scenarios.get(payload.scenario, {"objective": ScenarioObjective(main="", bonus=[], medal_conditions=[]), "prompt": ""})
    scenario_obj = scenario_data["objective"]
    scenario_prompt = scenario_data["prompt"]

    # Generate TTS for the prompt
    tts_client = ElevenLabsClient()
    personality = Personality(payload.personality)
    prompt_audio_bytes = await tts_client.generate_speech(scenario_prompt, personality)
    prompt_audio_b64 = base64.b64encode(prompt_audio_bytes).decode("utf-8") if prompt_audio_bytes else ""

    # Store session in SQLite DB
    from core.session_store import session_store
    session_store.save_session(session_id, {
        "user_id": payload.user_id,
        "mode": payload.mode,
        "scenario": payload.scenario,
        "personality": payload.personality,
        "objectives": scenario_obj.dict(),
        "prompt": scenario_prompt,
        "started_at": datetime.utcnow(),
        "calibration_completed": calibration_done
    })

    return {
        "session_id": session_id,
        "started_at": datetime.utcnow(),
        "mode": payload.mode,
        "scenario": payload.scenario,
        "personality": payload.personality,
        "objectives": scenario_obj,
        "prompt": scenario_prompt,
        "prompt_audio": prompt_audio_b64
    }

@router.post("/summary", response_model=SessionSummary)
def summarize_session(summary: SessionSummary):
    # placeholder: store to DB later
    return summary

@router.post("/end/{session_id}")
async def end_session(session_id: str):
    """
    End the session, compute accumulated FRS, and store summary in DB.
    """
    from core.session_store import session_store
    from api.routes.frs import accumulated_frs
    from core.scoring import FRSComputation
    from models.models import FRSResult
    from datetime import datetime

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get accumulated FRS scores
    frs_scores = accumulated_frs.get(session_id, [])
    if not frs_scores:
        # No FRS data accumulated, provide default feedback
        final_frs = FRSResult(
            charisma_friendliness=0.0,
            emotional_attunement_empathy=0.0,
            confidence_selfregulation=0.0,
            listening_reciprocal=0.0,
            frs_score=0.0,
            medals=[],
            stars_earned=0
        )
        feedback = {"overall": "No data collected. Please ensure the webcam stream runs for at least a few seconds to accumulate FRS scores."}
        objectives_completed = []
        stars_earned = 0
    else:
        # Compute average FRS result
        num_scores = len(frs_scores)
        avg_charisma_friendliness = sum(score['charisma_friendliness'] for score in frs_scores) / num_scores
        avg_emotional_attunement_empathy = sum(score['emotional_attunement_empathy'] for score in frs_scores) / num_scores
        avg_confidence_selfregulation = sum(score['confidence_selfregulation'] for score in frs_scores) / num_scores
        avg_listening_reciprocal = sum(score['listening_reciprocal'] for score in frs_scores) / num_scores
        avg_frs_score = sum(score['frs_score'] for score in frs_scores) / num_scores

        # Determine medals and stars from average FRS
        medals = []
        stars_earned = 1
        if avg_frs_score >= 8.5:
            medals.extend(["Charisma", "Friendliness", "Composure", "Awareness"])
            stars_earned = 4
        elif avg_frs_score >= 7.0:
            medals.extend(["Charisma", "Friendliness", "Composure"])
            stars_earned = 3
        elif avg_frs_score >= 5.5:
            medals.extend(["Friendliness", "Composure"])
            stars_earned = 2
        elif avg_frs_score >= 4.0:
            medals.append("Composure")
            stars_earned = 1

        # Additional medals based on averages
        if avg_charisma_friendliness > 0.8:
            if "Persuasion" not in medals:
                medals.append("Persuasion")
        if avg_emotional_attunement_empathy > 0.8:
            if "Compassion" not in medals:
                medals.append("Compassion")
        if avg_confidence_selfregulation > 0.8:
            if "Clarity" not in medals:
                medals.append("Clarity")
        if avg_listening_reciprocal > 0.8:
            if "Adaptability" not in medals:
                medals.append("Adaptability")

        # Create final FRS result
        final_frs = FRSResult(
            charisma_friendliness=round(avg_charisma_friendliness, 2),
            emotional_attunement_empathy=round(avg_emotional_attunement_empathy, 2),
            confidence_selfregulation=round(avg_confidence_selfregulation, 2),
            listening_reciprocal=round(avg_listening_reciprocal, 2),
            frs_score=round(avg_frs_score, 2),
            medals=medals,
            stars_earned=stars_earned
        )

        # Generate feedback based on scores
        feedback = {}
        if avg_frs_score >= 8.0:
            feedback["overall"] = "Excellent performance! You're a natural at social interactions."
        elif avg_frs_score >= 6.0:
            feedback["overall"] = "Good job! With a bit more practice, you'll excel."
        else:
            feedback["overall"] = "Keep practicing! Focus on eye contact and engagement."

        # Objectives completed (simulate based on session objectives)
        objectives_completed = session.get("objectives", {}).get("bonus", [])[:stars_earned]

    # Generate TTS for feedback
    tts_client = ElevenLabsClient()
    personality = Personality(session.get('personality', Personality.CALM.value))
    feedback_text = feedback.get("overall", "")
    feedback_audio_bytes = await tts_client.generate_speech(feedback_text, personality)
    feedback_audio_b64 = base64.b64encode(feedback_audio_bytes).decode("utf-8") if feedback_audio_bytes else ""

    # Store summary in DB
    summary_data = {
        'user_id': session['user_id'],
        'mode': session['mode'],
        'scenario': session['scenario'],
        'personality': session.get('personality'),
        'frs_result': final_frs.dict(),
        'feedback': feedback,
        'objectives_completed': objectives_completed,
        'stars_earned': stars_earned,
        'ended_at': datetime.utcnow()
    }
    emotion_summary = session_store.summarize_emotions(session_id)
    summary_data['emotion_summary'] = emotion_summary
    session_store.save_session_summary(session_id, summary_data)

    # Mark session as ended
    session['ended'] = True
    session_store.save_session(session_id, session)

    # Get conversation transcript from session_store
    conversation_history = session_store.get_full_transcript(session_id)
    transcript = [{"role": msg["speaker"], "content": msg["text"]} for msg in conversation_history]

    # Clean up accumulated scores
    if session_id in accumulated_frs:
        del accumulated_frs[session_id]

    return {
        "session_id": session_id,
        "final_frs": final_frs.dict(),
        "feedback": feedback,
        "feedback_audio": feedback_audio_b64,
        "objectives_completed": objectives_completed,
        "stars_earned": stars_earned,
        "transcript": transcript
    }

@router.get("/modes")
def get_modes():
    """
    Get available modes.
    """
    return {"modes": [mode.value for mode in Mode]}

@router.get("/scenarios/{mode}")
def get_scenarios(mode: str):
    """
    Get available scenarios for a specific mode.
    """
    mode_scenarios = scenarios.get(mode, {})
    return {"scenarios": list(mode_scenarios.keys())}

@router.get("/personalities")
def get_personalities():
    """
    Get available AI personalities.
    """
    from core.data_contract import Personality
    return {"personalities": [p.value for p in Personality]}

from pydantic import BaseModel

class UserMessage(BaseModel):
    user_message: str

class AudioMessage(BaseModel):
    audio: str  # base64 encoded audio

@router.post("/ai_response/{session_id}")
async def generate_ai_response(session_id: str, user_message: UserMessage):
    """
    Generate an AI response based on the session's personality, with voice synthesis.
    """
    from core.session_store import session_store
    from ai_personality import GPTClient
    from elevenlabs_client import ElevenLabsClient
    from core.data_contract import Personality

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    personality = session.get('personality')
    if not personality:
        raise HTTPException(status_code=400, detail="No personality set for this session")

    try:
        gpt_client = GPTClient()
        # Get conversation history from session store (assuming it's stored)
        conversation_history = session.get('conversation_history', [])
        response = await gpt_client.generate_response(user_message.user_message, Personality(personality), conversation_history)

        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message.user_message})
        conversation_history.append({"role": "assistant", "content": response})
        session['conversation_history'] = conversation_history[-20:]  # Keep last 20 messages
        session_store.save_session(session_id, session)

        # Generate voice audio with personality settings
        elevenlabs_client = ElevenLabsClient()
        audio_bytes = await elevenlabs_client.generate_speech(response, Personality(personality))

        # Return response with audio (base64 encoded for frontend)
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else ""

        return {
            "response": response,
            "personality": personality,
            "audio": audio_b64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI response: {str(e)}")

@router.post("/audio_response/{session_id}")
async def generate_audio_response(session_id: str, audio_message: AudioMessage):
    """
    Handle audio upload: STT → GPT → TTS → Return text + audio.
    """
    from core.session_store import session_store
    from ai_personality import GPTClient
    from elevenlabs_client import ElevenLabsClient
    from core.data_contract import Personality
    from hume_ai import analyze as hume_analyze
    from core.scoring import FRSComputation
    from api.routes.frs import accumulated_frs
    import base64
    import io
    from pydub import AudioSegment

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    personality = session.get('personality')
    if not personality:
        raise HTTPException(status_code=400, detail="No personality set for this session")

    try:
        gpt_client = GPTClient()
        elevenlabs_client = ElevenLabsClient()
        frs_engine = FRSComputation()

        # Decode base64 audio
        audio_b64 = audio_message.audio
        audio_bytes = base64.b64decode(audio_b64)

        # Convert audio to WAV if needed (assume WebM from frontend, convert to WAV for Whisper)
        try:
            webm_audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
            wav_buffer = io.BytesIO()
            webm_audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            setattr(wav_buffer, "name", "audio.wav")
            audio_for_stt = wav_buffer
        except Exception as e:
            # If conversion fails, assume it's already WAV/MP3
            audio_for_stt = io.BytesIO(audio_bytes)
            setattr(audio_for_stt, "name", "audio.wav")

        # Step 1: STT - Transcribe audio to text
        user_text = await gpt_client.transcribe_audio(audio_bytes)
        if not user_text:
            user_text = "[Transcription failed or no speech detected]"

        # Step 2: Analyze emotions with Hume AI (optional for FRS)
        emotions = {}
        try:
            emotions = await hume_analyze(audio_bytes, None)
        except Exception as e:
            print(f"Hume analysis failed: {e}")
            emotions = {"emotion_state": "neutral"}

        # Step 3: GPT processing
        conversation_history = session.get('conversation_history', [])
        response = await gpt_client.generate_response(user_text, Personality(personality), conversation_history)

        # Step 4: TTS - Generate speech
        audio_bytes_tts = await elevenlabs_client.generate_speech(response, Personality(personality))
        audio_b64_tts = base64.b64encode(audio_bytes_tts).decode('utf-8') if audio_bytes_tts else ""

        # Update conversation history
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": response})
        session['conversation_history'] = conversation_history[-20:]
        session_store.save_session(session_id, session)

        # Update FRS if emotions available
        if emotions:
            frs_score = frs_engine.update_metrics(session_id, emotions)
            accumulated_frs.setdefault(session_id, []).append(frs_score)

        return {
            "response": response,
            "audio": audio_b64_tts,
            "user_text": user_text,
            "emotions": emotions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process audio response: {str(e)}")


# ==============================================
# 🎙️ NEW: LIVE VOICE + BODY LANGUAGE STREAM
# ==============================================
@router.websocket("/voice-stream/{session_id}")
async def voice_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving live mic + body language stream.
    Flow:
      - Receive base64 audio chunks and optional body landmarks.
      - Send to Hume AI for emotional analysis.
      - Generate GPT response and voice synthesis.
      - Stream results (text + audio + emotions) back to the frontend.
    """
    await websocket.accept()
    from core.session_store import session_store
    from hume_ai import analyze as hume_analyze
    from ai_personality.gpt_client import GPTClient
    from elevenlabs_client import ElevenLabsClient
    from core.scoring import FRSComputation
    from api.routes.frs import accumulated_frs
    import base64

    gpt_client = GPTClient()
    tts_client = ElevenLabsClient()
    frs_engine = FRSComputation()

    try:
        session = session_store.get_session(session_id)
        if not session:
            await websocket.send_json({"error": "Session not found"})
            await websocket.close()
            return

        conversation_history = session.get("conversation_history", [])
        personality = session.get("personality", "default")

        while True:
            # Receive frontend message (audio, optional landmarks)
            data = await websocket.receive_text()
            payload = json.loads(data)

            audio_chunk = payload.get("audio")  # base64 encoded
            body_data = payload.get("body")      # pose/gesture data

            # Step 1️⃣: Send to Hume AI Stream for emotional analysis
            emotions = await hume_analyze(audio_chunk, body_data)

            # Step 2️⃣: Generate GPT response based on detected emotion + context
            user_text = payload.get("transcript", "")
            ai_response = await gpt_client.generate_response(
                user_text,
                personality=personality,
                conversation_history=conversation_history
            )

            # Step 3️⃣: Generate voice (TTS)
            audio_bytes = await tts_client.generate_speech(ai_response, personality)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else ""

            # Step 4️⃣: Update session & compute FRS
            conversation_history.append({"role": "user", "content": user_text})
            conversation_history.append({"role": "assistant", "content": ai_response})
            session["conversation_history"] = conversation_history[-20:]
            session_store.save_session(session_id, session)

            frs_score = frs_engine.update_metrics(session_id, emotions)
            accumulated_frs.setdefault(session_id, []).append(frs_score)

            # Step 5️⃣: Send response chunk to frontend
            await websocket.send_json({
                "response": ai_response,
                "audio": audio_b64,
                "emotions": emotions,
                "frs_update": frs_score
            })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        await websocket.send_json({"error": f"Internal error: {str(e)}"})
        await websocket.close()



@router.post("/calibrate")
async def calibrate(payload: dict):
    """
    Payload: { session_id: str, audio: base64-string }
    This endpoint stores a baseline sample — real implementation should analyze calibration sample using Hume
    and store baseline feature vector per user. For now we store the raw audio or a computed baseline summary.
    """
    session_id = payload.get("session_id")
    audio_b64 = payload.get("audio")
    if not session_id or not audio_b64:
        raise HTTPException(status_code=400, detail="session_id and audio required")

    # decode and optionally run a quick Hume analysis to get baseline features
    audio_bytes = base64.b64decode(audio_b64)
    baseline = {}
    try:
        # If you have a lightweight hume analyze callable for small audio, use it:
        baseline = await hume_analyze(audio_bytes, None)
    except Exception as e:
        print("Calibration Hume analyze failed:", e)
        # fallback baseline (neutral)
        baseline = {"eye_contact": 0.0, "smile": 0.0, "vocal_tone": 0.0, "pacing": 0.0, "engagement": 0.0}

    session = session_store.get_session(session_id) or {}
    session['calibration'] = baseline
    session_store.save_session(session_id, session)
    return {"status": "ok", "baseline": baseline}
