from pydantic import BaseModel
from typing import Optional, Dict, List
from enum import StrEnum
from core.data_contract import Mode

class CalibrationStep(BaseModel):
    step_id: str
    instruction: str
    line_to_read: Optional[str] = None
    expression: Optional[str] = None
    gesture: Optional[str] = None

class CalibrationData(BaseModel):
    user_id: str
    steps_completed: List[str]
    baseline_emotions: Dict[str, float]

class SessionCreate(BaseModel):
    user_id: str
    mode: Mode
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
    charisma_friendliness: float
    emotional_attunement_empathy: float
    confidence_selfregulation: float
    listening_reciprocal: float
    frs_score: float
    medals: List[str]
    stars_earned: int

class ScenarioObjective(BaseModel):
    main: str
    bonus: List[str]
    medal_conditions: List[str]
    dynamic_objectives: Optional[List[str]] = None

class SessionSummary(BaseModel):
    session_id: str
    user_id: str
    mode: Mode
    scenario: str
    frs_result: FRSResult
    feedback: Optional[Dict[str, str]] = None
    objectives_completed: Optional[List[str]] = None
    stars_earned: int
