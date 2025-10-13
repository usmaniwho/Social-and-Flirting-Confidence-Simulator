
from fastapi import APIRouter
from models.models import SessionCreate, SessionSummary, FRSResult, ScenarioObjective
from datetime import datetime
import uuid

router = APIRouter()

# Scenario definitions
scenarios = {
    "first_date_jitters": ScenarioObjective(
        main="Deepen conversation",
        bonus=["Eye contact", "Anecdotes", "Reciprocity"],
        medal_conditions=["Charisma", "Friendliness", "Composure"]
    ),
    "house_party": ScenarioObjective(
        main="Join conversation naturally",
        bonus=["Eye contact", "Smile", "Initiate contact"],
        medal_conditions=["Friendliness", "Composure"]
    ),
    "bar_invite": ScenarioObjective(
        main="Break ice and have 3-exchange interaction",
        bonus=["Make observational joke", "Maintain eye contact", "Leave with agreement to meet again"],
        medal_conditions=["Charisma", "Friendliness"]
    )
}

@router.post("/start")
def start_session(payload: SessionCreate):
    session_id = str(uuid.uuid4())
    scenario_obj = scenarios.get(payload.scenario, ScenarioObjective(main="", bonus=[], medal_conditions=[]))
    return {
        "session_id": session_id,
        "started_at": datetime.utcnow(),
        "scenario": payload.scenario,
        "objectives": scenario_obj
    }

@router.post("/summary", response_model=SessionSummary)
def summarize_session(summary: SessionSummary):
    # placeholder: store to DB later
    return summary

@router.get("/scenarios")
def get_scenarios():
    """
    Get available scenarios.
    """
    return {"scenarios": list(scenarios.keys())}
