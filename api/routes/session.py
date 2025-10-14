from fastapi import APIRouter, HTTPException
from models.models import SessionCreate, SessionSummary, FRSResult, ScenarioObjective, Mode
from datetime import datetime
import uuid

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
                main="Deepen conversation and build connection",
                bonus=["Eye contact", "Share anecdotes", "Show reciprocity"],
                medal_conditions=["Charisma", "Friendliness", "Composure", "Compassion"],
                dynamic_objectives=["Build trust quickly", "Respond well to awkward silence"]
            ),
            "prompt": "You're on your first date and feeling a bit nervous. The conversation needs to flow naturally."
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
def start_session(payload: SessionCreate):
    session_id = str(uuid.uuid4())
    mode_scenarios = scenarios.get(payload.mode, {})
    scenario_data = mode_scenarios.get(payload.scenario, {"objective": ScenarioObjective(main="", bonus=[], medal_conditions=[]), "prompt": ""})
    scenario_obj = scenario_data["objective"]
    scenario_prompt = scenario_data["prompt"]

    # Store session in SQLite DB
    from core.session_store import session_store
    session_store.save_session(session_id, {
        "user_id": payload.user_id,
        "mode": payload.mode,
        "scenario": payload.scenario,
        "personality": payload.personality,
        "objectives": scenario_obj.dict(),
        "prompt": scenario_prompt,
        "started_at": datetime.utcnow()
    })

    return {
        "session_id": session_id,
        "started_at": datetime.utcnow(),
        "mode": payload.mode,
        "scenario": payload.scenario,
        "personality": payload.personality,
        "objectives": scenario_obj,
        "prompt": scenario_prompt
    }

@router.post("/summary", response_model=SessionSummary)
def summarize_session(summary: SessionSummary):
    # placeholder: store to DB later
    return summary

@router.post("/end/{session_id}")
def end_session(session_id: str):
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
    session_store.save_session_summary(session_id, summary_data)

    # Clean up accumulated scores
    if session_id in accumulated_frs:
        del accumulated_frs[session_id]

    return {
        "session_id": session_id,
        "final_frs": final_frs.dict(),
        "feedback": feedback,
        "objectives_completed": objectives_completed,
        "stars_earned": stars_earned
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

        # Generate voice audio
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
