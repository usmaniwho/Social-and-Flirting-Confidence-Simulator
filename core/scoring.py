from models.models import EmotionData, FRSResult, BaselineData, Medal

class FRSComputation:
    @staticmethod
    def compute_frs(data: EmotionData, baseline: BaselineData = None) -> FRSResult:
        """
        Compute the FRS (Fluency & Readiness Score) from emotion data, compared to baseline.
        Factors: Charisma & Friendliness, Emotional Attunement & Empathy, Confidence & Self-Regulation, Listening & Reciprocal Dialogue
        """
        # Calculate components based on new factors
        charisma_friendliness = (data.smile + data.engagement) / 2.0  # Smile and engagement indicate friendliness/charisma
        emotional_attunement_empathy = (data.eye_contact + data.engagement) / 2.0  # Eye contact and engagement for attunement
        confidence_selfregulation = (data.vocal_tone + data.pacing) / 2.0  # Vocal tone and pacing for confidence
        listening_reciprocal = (data.eye_contact + data.vocal_tone) / 2.0  # Eye contact and vocal tone for listening

        # If baseline provided, compare performance
        if baseline:
            charisma_friendliness = max(0, charisma_friendliness - ((baseline.smile + baseline.engagement) / 2.0))
            emotional_attunement_empathy = max(0, emotional_attunement_empathy - ((baseline.eye_contact + baseline.engagement) / 2.0))
            confidence_selfregulation = max(0, confidence_selfregulation - ((baseline.vocal_tone + baseline.pacing) / 2.0))
            listening_reciprocal = max(0, listening_reciprocal - ((baseline.eye_contact + baseline.vocal_tone) / 2.0))

        # Weighted FRS score (0-10 scale)
        frs_score = (charisma_friendliness * 0.25 + emotional_attunement_empathy * 0.25 +
                    confidence_selfregulation * 0.25 + listening_reciprocal * 0.25) * 10

        # Determine medals based on FRS score and traits
        medals = []
        stars_earned = 1  # Base star for completing session

        if frs_score >= 8.5:
            medals.extend([Medal.CHARISMA, Medal.FRIENDLINESS, Medal.COMPOSURE, Medal.AWARENESS])
            stars_earned = 4
        elif frs_score >= 7.0:
            medals.extend([Medal.CHARISMA, Medal.FRIENDLINESS, Medal.COMPOSURE])
            stars_earned = 3
        elif frs_score >= 5.5:
            medals.extend([Medal.FRIENDLINESS, Medal.COMPOSURE])
            stars_earned = 2
        elif frs_score >= 4.0:
            medals.append(Medal.COMPOSURE)
            stars_earned = 1

        # Additional medals based on specific thresholds
        if charisma_friendliness > 0.8:
            if Medal.PERSUASION not in medals:
                medals.append(Medal.PERSUASION)
        if emotional_attunement_empathy > 0.8:
            if Medal.COMPASSION not in medals:
                medals.append(Medal.COMPASSION)
        if confidence_selfregulation > 0.8:
            if Medal.CLARITY not in medals:
                medals.append(Medal.CLARITY)
        if listening_reciprocal > 0.8:
            if Medal.ADAPTABILITY not in medals:
                medals.append(Medal.ADAPTABILITY)

        return FRSResult(
            charisma_friendliness=round(charisma_friendliness, 2),
            emotional_attunement_empathy=round(emotional_attunement_empathy, 2),
            confidence_selfregulation=round(confidence_selfregulation, 2),
            listening_reciprocal=round(listening_reciprocal, 2),
            frs_score=round(frs_score, 2),
            medals=medals,
            stars_earned=stars_earned
        )
