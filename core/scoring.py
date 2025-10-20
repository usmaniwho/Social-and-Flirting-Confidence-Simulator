# core/scoring.py
# FRS computation engine
# 🔧 Implements the 35% visual / 40% vocal / 25% emotional weighting and returns
#    a per-update FRSResult-like dict for immediate frontend feedback and accumulation.

from typing import Dict, Any
import math

class FRSComputation:
    """
    FRSComputation - update_metrics(session_id, emotions) returns a dict:
      {
        "charisma_friendliness": float(0-10),
        "emotional_attunement_empathy": float(0-10),
        "confidence_selfregulation": float(0-10),
        "listening_reciprocal": float(0-10),
        "frs_score": float(0-10),
        "medals": [...optional...]
      }
    """

    def __init__(self):
        # Tunable multipliers / thresholds can be calibrated independently later
        self.weights = {
            "visual": 0.35,   # visual confidence
            "vocal": 0.40,    # vocal fluency
            "emotional": 0.25 # emotional awareness
        }

    def _scale(self, value: float) -> float:
        """Ensure a [0..1] value to 0..10 scale"""
        return max(0.0, min(1.0, value)) * 10.0

    def _visual_score(self, emotions: Dict[str, Any]) -> float:
        """
        Visual Confidence (35%)
        Use eye_contact, smile, engagement (face)
        """
        eye = emotions.get("eye_contact", 0.0)
        smile = emotions.get("smile", 0.0)
        engagement = emotions.get("engagement", 0.0)
        # Weighted visual features (tunable)
        visual_raw = 0.5 * eye + 0.35 * smile + 0.15 * engagement
        return self._scale(visual_raw)

    def _vocal_score(self, emotions: Dict[str, Any]) -> float:
        """
        Vocal Fluency (40%)
        Use vocal_tone, pacing, clarity (if available)
        """
        vocal = emotions.get("vocal_tone", 0.0)
        pacing = emotions.get("pacing", 0.0)
        # If 'fluency' or 'clarity' provided by Hume, they can be used here
        clarity = emotions.get("clarity", None)
        if clarity is None:
            vocal_raw = 0.6 * vocal + 0.4 * pacing
        else:
            vocal_raw = 0.5 * vocal + 0.35 * pacing + 0.15 * clarity
        return self._scale(vocal_raw)

    def _emotional_score(self, emotions: Dict[str, Any]) -> float:
        """
        Emotional Awareness (25%)
        Use empathy-like signals: engagement, emotion_state mapping (e.g., 'happy' or 'focused' may boost)
        """
        engagement = emotions.get("engagement", 0.0)
        emotion_state = emotions.get("emotion_state", "neutral")
        # Map states to a small bonus
        state_bonus_map = {
            "happy": 0.1,
            "focused": 0.1,
            "neutral": 0.0,
            "disengaged": -0.15,
            "excited": 0.05,
            "stressed": -0.2
        }
        bonus = state_bonus_map.get(emotion_state, 0.0)
        emotional_raw = max(0.0, min(1.0, engagement + bonus))
        return self._scale(emotional_raw)

    def update_metrics(self, session_id: str, emotions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main call for the realtime pipeline.
        Returns the component scores and composite FRS score.
        """
        visual = self._visual_score(emotions)
        vocal = self._vocal_score(emotions)
        emotional = self._emotional_score(emotions)

        # For personality traits (charisma, etc.) we derive from component mix:
        # - charisma_friendliness: favors visual + emotional
        charisma = (0.6 * visual + 0.4 * emotional)
        # - emotional_attunement_empathy: emotional + visual
        empathy = (0.7 * emotional + 0.3 * visual)
        # - confidence_selfregulation: vocal + visual
        confidence = (0.7 * vocal + 0.3 * visual)
        # - listening_reciprocal: vocal pacing + engagement
        listening = (0.6 * vocal + 0.4 * emotional)

        # Composite FRS (0-10)
        frs_score = (self.weights["visual"] * visual +
                     self.weights["vocal"] * vocal +
                     self.weights["emotional"] * emotional)

        # Basic medal heuristics — simple thresholds (calibrate later)
        from core.data_contract import MedalThresholds
        medals = []
        if charisma >= MedalThresholds.CHARISMA_MIN:
            medals.append("Charisma")
        if empathy >= MedalThresholds.EMPATHY_MIN:
            medals.append("Compassion")
        if confidence >= MedalThresholds.CONFIDENCE_MIN:
            medals.append("Composure")
        if listening >= MedalThresholds.LISTENING_MIN:
            medals.append("Adaptability")

        # Return nicely rounded values
        def r(x): return round(x, 2)
        return {
            "charisma_friendliness": r(charisma),
            "emotional_attunement_empathy": r(empathy),
            "confidence_selfregulation": r(confidence),
            "listening_reciprocal": r(listening),
            "frs_score": r(frs_score),
            "medals": medals
        }

    @staticmethod
    def compute_frs(data: 'EmotionData', baseline: 'BaselineData' = None) -> 'FRSResult':
        """
        Static method to compute FRS score from emotion data and optional baseline.
        Compares current performance to baseline if provided.
        """
        instance = FRSComputation()
        emotions = {
            "eye_contact": data.eye_contact,
            "smile": data.smile,
            "vocal_tone": data.vocal_tone,
            "pacing": data.pacing,
            "engagement": data.engagement
        }

        # Adjust for baseline if available
        if baseline:
            emotions["eye_contact"] = max(0, emotions["eye_contact"] - baseline.eye_contact)
            emotions["smile"] = max(0, emotions["smile"] - baseline.smile)
            emotions["vocal_tone"] = max(0, emotions["vocal_tone"] - baseline.vocal_tone)
            emotions["pacing"] = max(0, emotions["pacing"] - baseline.pacing)
            emotions["engagement"] = max(0, emotions["engagement"] - baseline.engagement)

        result = instance.update_metrics("temp", emotions)

        from models.models import FRSResult
        return FRSResult(
            charisma_friendliness=result["charisma_friendliness"],
            emotional_attunement_empathy=result["emotional_attunement_empathy"],
            confidence_selfregulation=result["confidence_selfregulation"],
            listening_reciprocal=result["listening_reciprocal"],
            frs_score=result["frs_score"],
            medals=result["medals"],
            stars_earned=1  # Default, can be calculated based on score
        )
