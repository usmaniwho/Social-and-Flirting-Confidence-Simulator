from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import io
from ai_personality import GPTClient
from elevenlabs_client import ElevenLabsClient
from core.session_store import session_store
from core.data_contract import Personality

router = APIRouter()

@router.post("/conversation")
async def conversation(request: Request):
    data = await request.json()
    user_message = data.get("message")
    session_id = data.get("session_id")
    user_id = data.get("user_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    personality = session.get('personality')
    if not personality:
        personality = Personality.friendly  # Default

    conversation_history = session.get('conversation_history', [])

    try:
        gpt_client = GPTClient()
        response = await gpt_client.generate_response(user_message, Personality(personality), conversation_history)

        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": response})
        session['conversation_history'] = conversation_history[-20:]  # Keep last 20 messages
        session_store.save_session(session_id, session)

        return {"reply": response}
    except Exception as e:
        print(f"Error in conversation endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate conversation response: {str(e)}")

@router.post("/voice")
async def voice(request: Request):
    data = await request.json()
    text = data.get("text")
    session_id = data.get("session_id")

    if not text or not session_id:
        raise HTTPException(status_code=400, detail="Text and session_id required")

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    personality = session.get('personality')
    if not personality:
        personality = Personality.friendly

    try:
        elevenlabs_client = ElevenLabsClient()
        audio_bytes = await elevenlabs_client.generate_speech(text, Personality(personality))

        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate voice: {str(e)}")
