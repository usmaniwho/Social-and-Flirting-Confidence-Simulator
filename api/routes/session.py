
from fastapi import APIRouter, HTTPException
from models.models import SessionCreate, SessionSummary, FRSResult, ScenarioObjective, Mode
from datetime import datetime
import uuid

router = APIRouter()

# Expanded scenario definitions with modes
scenarios = {
    "social": {
        "house_party": ScenarioObjective(
            main="Join conversation naturally",
            bonus=["Eye contact", "Smile", "Initiate contact"],
            medal_conditions=["Friendliness", "Composure", "Adaptability"],
            dynamic_objectives=["Make a new friend", "Build trust quickly"]
        ),
        "work_mixer": ScenarioObjective(
            main="Navigate casual group dynamics",
            bonus=["Listen first", "Contribute usefully", "Include others"],
            medal_conditions=["Friendliness", "Awareness", "Composure"],
            dynamic_objectives=["Get invited to an event", "Establish common ground"]
        ),
        "group_conversation": ScenarioObjective(
            main="Participate effectively in group setting",
            bonus=["Listen first", "Contribute usefully", "Include others"],
            medal_conditions=["Friendliness", "Composure", "Awareness"],
            dynamic_objectives=["Make a new friend", "Build trust quickly"]
        )
    },
    "romantic": {
        "bar_encounter": ScenarioObjective(
            main="Start a conversation and keep it flowing",
            bonus=["Make an observational joke", "Maintain eye contact", "Use subtle flattery"],
            medal_conditions=["Charisma", "Friendliness", "Persuasion"],
            dynamic_objectives=["Ask someone out", "Build attraction", "Escalate connection"]
        ),
        "first_date_jitters": ScenarioObjective(
            main="Deepen conversation and build connection",
            bonus=["Eye contact", "Share anecdotes", "Show reciprocity"],
            medal_conditions=["Charisma", "Friendliness", "Composure", "Compassion"],
            dynamic_objectives=["Build trust quickly", "Respond well to awkward silence"]
        ),
        "coffee_shop_approach": ScenarioObjective(
            main="Break the ice and have meaningful interaction",
            bonus=["Tease respectfully", "Listen actively", "Respond smoothly"],
            medal_conditions=["Charisma", "Friendliness", "Awareness"],
            dynamic_objectives=["Leave with verbal agreement to meet again", "Establish common ground"]
        )
    }
}

@router.post("/start")
def start_session(payload: SessionCreate):
    session_id = str(uuid.uuid4())
    mode_scenarios = scenarios.get(payload.mode, {})
    scenario_obj = mode_scenarios.get(payload.scenario, ScenarioObjective(main="", bonus=[], medal_conditions=[]))

    # Store session in SQLite DB
    from core.session_store import session_store
    session_store.save_session(session_id, {
        "user_id": payload.user_id,
        "mode": payload.mode,
        "scenario": payload.scenario,
        "objectives": scenario_obj.dict(),
        "started_at": datetime.utcnow()
    })

    return {
        "session_id": session_id,
        "started_at": datetime.utcnow(),
        "mode": payload.mode,
        "scenario": payload.scenario,
        "objectives": scenario_obj
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
