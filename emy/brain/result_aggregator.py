"""Aggregate results from multiple agents."""

import logging
from typing import Dict, Any, List
from statistics import mean

logger = logging.getLogger('EMyBrain.ResultAggregator')


class ResultAggregator:
    """Aggregate and normalize results from multiple agents."""

    def aggregate(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.

        Args:
            results: Dict mapping agent name to result dict

        Returns:
            Aggregated result with consensus and conflict detection
        """
        if not results:
            return {
                'agents': {},
                'consensus': None,
                'conflict_detected': False,
                'conflicts': []
            }

        # Normalize all recommendations to comparable format
        normalized = {}
        recommendations = {}
        confidences = []

        for agent_name, result in results.items():
            normalized[agent_name] = result
            recommendations[agent_name] = self._normalize_recommendation(result.get('recommendation', ''))
            if 'confidence' in result:
                confidences.append(result['confidence'])

        # Check for conflicts
        unique_recs = set(recommendations.values())
        has_conflict = len(unique_recs) > 1 and len(results) > 1

        conflicts = []
        if has_conflict:
            conflicts = self._find_conflicts(recommendations)

        # Calculate consensus
        consensus = None
        if not has_conflict and recommendations:
            consensus = {
                'recommendation': list(recommendations.values())[0],
                'confidence': mean(confidences) if confidences else 0.0,
                'agent_count': len(results)
            }

        return {
            'agents': normalized,
            'consensus': consensus,
            'conflict_detected': has_conflict,
            'conflicts': conflicts
        }

    def _normalize_recommendation(self, rec: str) -> str:
        """
        Normalize recommendation to comparable format.

        Args:
            rec: Recommendation text

        Returns:
            Normalized recommendation (e.g., 'SELL', 'BUY', 'HOLD')
        """
        rec_upper = rec.upper().strip()

        # Extract main recommendation
        for keyword in ['SELL', 'BUY', 'HOLD']:
            if keyword in rec_upper:
                return keyword

        return rec_upper

    def _find_conflicts(self, recommendations: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Identify conflicting recommendations.

        Args:
            recommendations: Dict mapping agent to normalized recommendation

        Returns:
            List of conflict records
        """
        conflicts = []
        recs_list = list(recommendations.items())

        for i, (agent1, rec1) in enumerate(recs_list):
            for agent2, rec2 in recs_list[i+1:]:
                if rec1 != rec2:
                    conflicts.append({
                        'agent1': agent1,
                        'agent2': agent2,
                        'rec1': rec1,
                        'rec2': rec2
                    })

        return conflicts
