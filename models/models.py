from pydantic import BaseModel
from typing import Optional, Dict, List
from enum import StrEnum
from core.data_contract import Mode, Personality

class CalibrationStep(BaseModel):
    step_id: str
    instruction: str
    line_to_read: Optional[str] = None
    expression: Optional[str] = None
    gesture: Optional[str] = None

class CalibrationData(BaseModel):
    user_id: str
    steps_completed: List[str]
    baseline_emotions: Dict[str, Dict[str, float]]  # Changed to Dict[str, Dict[str, float]] for per-step emotions

class CalibrateStepRequest(BaseModel):
    user_id: str
    step_id: str
    audio: Optional[str] = None
    video: Optional[str] = None

class ConversationTranscript(BaseModel):
    session_id: str
    transcript: List[Dict[str, str]]  # List of {"role": "user" or "assistant", "content": text}

class SessionCreate(BaseModel):
    user_id: str
    mode: Mode
    scenario: str
    personality: Optional[Personality] = None

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
    personality: Optional[Personality] = None
    frs_result: FRSResult
    feedback: Optional[Dict[str, str]] = None
    objectives_completed: Optional[List[str]] = None
    stars_earned: int
