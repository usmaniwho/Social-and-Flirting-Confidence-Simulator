from enum import StrEnum

class DocumentationSections(StrEnum):
    DOCUMENTATION = "DOCUMENTATION"
    FRS = "FRS"

class Mode(StrEnum):
    SOCIAL = "social"
    ROMANTIC = "romantic"

class Personality(StrEnum):
    PLAYFUL = "playful"
    CALM = "calm"
    SHY = "shy"

class Medal(StrEnum):
    FRIENDLINESS = "Friendliness"
    COMPOSURE = "Composure"
    COMPASSION = "Compassion"
    CHARISMA = "Charisma"
    ADAPTABILITY = "Adaptability"
    CLARITY = "Clarity"
    AWARENESS = "Awareness"
    PERSUASION = "Persuasion"

class CalibrationThresholds:
    """Thresholds for calibration step validation"""
    VOCAL_TONE_MIN = 0.0  # Very low threshold to always pass for demo
    ENGAGEMENT_VOICE_MIN = 0.0  # Very low threshold to always pass for demo
    SMILE_MIN = 0.0  # Very low threshold to always pass for demo
    EYE_CONTACT_MIN = 0.0  # Very low threshold to always pass for demo
    ENGAGEMENT_GESTURE_MIN = 0.0  # Very low threshold to always pass for demo

class MedalThresholds:
    """Thresholds for awarding medals based on FRS components"""
    CHARISMA_MIN = 8.0
    EMPATHY_MIN = 7.5
    CONFIDENCE_MIN = 7.0
    LISTENING_MIN = 7.0

class FeedbackThresholds:
    """Thresholds for session feedback generation"""
    EXCELLENT_MIN = 8.0
    GOOD_MIN = 6.0
    DECENT_MIN = 4.0
