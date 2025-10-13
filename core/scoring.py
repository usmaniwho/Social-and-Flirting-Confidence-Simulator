from models.models import EmotionData, FRSResult, BaselineData

class FRSComputation:
    @staticmethod
    def compute_frs(data: EmotionData, baseline: BaselineData = None) -> FRSResult:
        """
        Compute the FRS (Fluency-Reciprocity-Score) from emotion data, compared to baseline.
        Weights: Visual Confidence 35%, Vocal Fluency 40%, Emotional Awareness 25%
        """
        # Calculate components
        visual_confidence = (data.eye_contact + data.smile) / 2.0
        vocal_fluency = (data.vocal_tone + data.pacing) / 2.0  # Adjusted for new fields
        emotional_awareness = data.engagement  # Using engagement as proxy

        # If baseline provided, compare performance
        if baseline:
            visual_confidence = max(0, visual_confidence - ((baseline.eye_contact + baseline.smile) / 2.0))
            vocal_fluency = max(0, vocal_fluency - ((baseline.vocal_tone + baseline.pacing) / 2.0))
            emotional_awareness = max(0, emotional_awareness - baseline.engagement)

        # Weighted FRS score (0-10 scale)
        frs_score = (visual_confidence * 0.35 + vocal_fluency * 0.40 + emotional_awareness * 0.25) * 10

        # Determine medals based on FRS score and traits
        medals = []
        if frs_score >= 8.0:
            medals.extend(["Charisma", "Friendliness", "Composure"])
        elif frs_score >= 6.0:
            medals.extend(["Friendliness", "Composure"])
        elif frs_score >= 4.0:
            medals.append("Composure")

        return FRSResult(
            visual_confidence=round(visual_confidence, 2),
            vocal_fluency=round(vocal_fluency, 2),
            emotional_awareness=round(emotional_awareness, 2),
            frs_score=round(frs_score, 2),
            medals=medals
        )
