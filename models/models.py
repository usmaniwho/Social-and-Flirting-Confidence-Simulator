from pydantic import BaseModel
from typing import Optional, Dict, List

class SessionCreate(BaseModel):
    user_id: str
    scenario: str

class EmotionData(BaseModel):
    eye_contact: float
    smile: float
    vocal_tone: float
    pacing: float
    engagement: float

class BaselineData(BaseModel):
    eye_contact: float
    smile: float
    vocal_tone: float
    pacing: float
    engagement: float

class FRSResult(BaseModel):
    visual_confidence: float
    vocal_fluency: float
    emotional_awareness: float
    frs_score: float
    medals: List[str]

class ScenarioObjective(BaseModel):
    main: str
    bonus: List[str]
    medal_conditions: List[str]

class SessionSummary(BaseModel):
    session_id: str
    user_id: str
    scenario: str
    frs_result: FRSResult
    feedback: Optional[Dict[str, str]] = None
    objectives_completed: Optional[List[str]] = None
