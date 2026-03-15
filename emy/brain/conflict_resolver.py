"""Resolve conflicts between agent recommendations."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('EMyBrain.ConflictResolver')


class ConflictResolver:
    """Resolve conflicts between agent recommendations."""

    def __init__(self, agent_weights: Optional[Dict[str, float]] = None):
        """
        Initialize conflict resolver.

        Args:
            agent_weights: Optional weights for agents (default 1.0 for all)
        """
        self.agent_weights = agent_weights or {}

    def resolve(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve conflicts in agent results.

        Args:
            results: Dict mapping agent name to result

        Returns:
            Resolved recommendation with metadata
        """
        if not results:
            return {'recommendation': None, 'conflict_detected': False}

        # Extract recommendations and confidences
        agents_data = {}
        for agent_name, result in results.items():
            confidence = result.get('confidence', 0.5)
            recommendation = result.get('recommendation', '').upper().strip()

            # Extract main recommendation
            for keyword in ['SELL', 'BUY', 'HOLD']:
                if keyword in recommendation:
                    recommendation = keyword
                    break

            weight = self.agent_weights.get(agent_name, 1.0)
            agents_data[agent_name] = {
                'recommendation': recommendation,
                'confidence': confidence,
                'weight': weight,
                'weighted_confidence': confidence * weight
            }

        # Check if unanimous
        unique_recs = set(a['recommendation'] for a in agents_data.values())
        if len(unique_recs) == 1:
            winning_rec = unique_recs.pop()
            avg_confidence = sum(a['confidence'] for a in agents_data.values()) / len(agents_data)

            return {
                'recommendation': winning_rec,
                'resolution_method': 'unanimous',
                'confidence': avg_confidence,
                'agents_agreeing': list(agents_data.keys()),
                'conflict_detected': False
            }

        # Check weighted voting
        if self.agent_weights:
            scores = {}
            for agent, data in agents_data.items():
                rec = data['recommendation']
                scores[rec] = scores.get(rec, 0) + data['weighted_confidence']

            winning_rec = max(scores, key=scores.get)
            winning_agent = [a for a, d in agents_data.items()
                           if d['recommendation'] == winning_rec][0]

            return {
                'recommendation': winning_rec,
                'resolution_method': 'weighted_voting',
                'confidence': agents_data[winning_agent]['confidence'],
                'winning_agent': winning_agent,
                'conflict_detected': True,
                'conflict_severity': self._assess_severity(agents_data)
            }

        # Resolve by highest confidence
        best_agent = max(agents_data.items(),
                        key=lambda x: x[1]['confidence'])
        winning_agent, best_data = best_agent

        # Flag for review if close call
        flag_for_review = False
        review_reason = None

        confidences = [a['confidence'] for a in agents_data.values()]
        if len(confidences) > 1:
            top2 = sorted(confidences, reverse=True)[:2]
            if abs(top2[0] - top2[1]) < 0.15:  # Within 15%
                flag_for_review = True
                review_reason = f"Close call: top confidence {top2[0]:.2f} vs {top2[1]:.2f}"

        return {
            'recommendation': best_data['recommendation'],
            'resolution_method': 'highest_confidence',
            'confidence': best_data['confidence'],
            'winning_agent': winning_agent,
            'conflict_detected': True,
            'conflict_severity': self._assess_severity(agents_data),
            'flag_for_review': flag_for_review,
            'review_reason': review_reason
        }

    def _assess_severity(self, agents_data: Dict[str, Dict[str, Any]]) -> str:
        """
        Assess conflict severity.

        Args:
            agents_data: Agent data with recommendations

        Returns:
            'low', 'medium', or 'high'
        """
        unique_recs = len(set(a['recommendation'] for a in agents_data.values()))

        if unique_recs == 2:
            return 'low'
        elif unique_recs >= 3:
            return 'high'
        else:
            return 'low'
