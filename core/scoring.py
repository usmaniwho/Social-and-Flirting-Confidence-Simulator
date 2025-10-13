from models.models import EmotionData, FRSResult, BaselineData, Medal

class FRSComputation:
    @staticmethod
    def compute_frs(data: EmotionData, baseline: BaselineData = None) -> FRSResult:
        """
        Compute the FRS (Fluency & Readiness Score) from emotion data, compared to baseline.
        New weights: Visual Confidence 35%, Vocal Fluency 40%, Emotional Awareness 25%
        """
        # Calculate new components
        visual_confidence = (data.eye_contact + data.smile) / 2.0  # Eye contact and smile for visual confidence
        vocal_fluency = (data.vocal_tone + data.pacing) / 2.0  # Vocal tone and pacing for vocal fluency
        emotional_awareness = data.engagement  # Engagement for emotional awareness

        # If baseline provided, compare performance (reduced threshold for higher scores)
        if baseline:
            baseline_visual = (baseline.eye_contact + baseline.smile) / 2.0
            baseline_vocal = (baseline.vocal_tone + baseline.pacing) / 2.0
            visual_confidence = max(0, visual_confidence - 0.5 * baseline_visual)
            vocal_fluency = max(0, vocal_fluency - 0.5 * baseline_vocal)
            emotional_awareness = max(0, emotional_awareness - 0.5 * baseline.engagement)

        # Weighted FRS score (0-10 scale) with new percentages
        frs_score = (visual_confidence * 0.35 + vocal_fluency * 0.40 + emotional_awareness * 0.25) * 10

        # Map to existing breakdown for compatibility
        charisma_friendliness = visual_confidence
        emotional_attunement_empathy = emotional_awareness
        confidence_selfregulation = vocal_fluency
        listening_reciprocal = (data.eye_contact + data.vocal_tone) / 2.0  # Keep for listening aspect
        if baseline:
            listening_reciprocal = max(0, listening_reciprocal - ((baseline.eye_contact + baseline.vocal_tone) / 2.0))

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
