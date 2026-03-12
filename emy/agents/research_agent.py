"""
ResearchAgent - evaluates new projects for feasibility.

Analyzes project requirements, identifies technical risks, and recommends priority.
Used for evaluating Currency-Trend-Tracker, Recruiter-Email-Automation, etc.
"""

import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger('ResearchAgent')


class ResearchAgent:
    """Agent for researching and evaluating new projects."""

    def __init__(self):
        """Initialize research agent."""
        self.logger = logging.getLogger('ResearchAgent')

    def run(self, task_id: int = None, project_name: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Research and evaluate a project.

        Args:
            task_id: Associated task ID in database
            project_name: Name of project to research

        Returns:
            (success, results) tuple
        """
        try:
            self.logger.info(f"[RUN] ResearchAgent starting for project: {project_name}")

            # Check disable guard
            from emy.core.disable_guard import EMyDisableGuard
            disable_guard = EMyDisableGuard()
            if disable_guard.is_disabled():
                return False, {'error': 'Emy disabled'}

            if not project_name:
                return False, {'error': 'project_name required'}

            results = {
                'timestamp': self._get_timestamp(),
                'project': project_name,
                'feasibility_score': 0.0,
                'estimated_effort_hours': 0,
                'key_dependencies': [],
                'technical_risks': [],
                'recommendation': 'pending'
            }

            # Analyze project
            analysis = self._analyze_project(project_name)
            if not analysis:
                return False, {'error': f'Failed to analyze {project_name}'}

            results.update(analysis)

            # Calculate feasibility score
            results['feasibility_score'] = self._calculate_feasibility(analysis)

            # Make recommendation
            if results['feasibility_score'] >= 0.75:
                results['recommendation'] = 'high_priority'
            elif results['feasibility_score'] >= 0.50:
                results['recommendation'] = 'medium_priority'
            else:
                results['recommendation'] = 'low_priority'

            self.logger.info(
                f"[RUN] ResearchAgent completed: "
                f"{project_name} → {results['recommendation']} "
                f"(score: {results['feasibility_score']:.1%})"
            )
            return True, results

        except Exception as e:
            self.logger.error(f"[RUN] ResearchAgent error: {e}")
            return False, {'error': str(e)}

    def _analyze_project(self, project_name: str) -> Dict[str, Any]:
        """Analyze project for feasibility."""
        try:
            # Map known projects to their analysis
            projects_db = {
                'currency_trend_tracker': {
                    'description': 'Real-time currency trend analysis with ML predictions',
                    'key_dependencies': ['pandas', 'scikit-learn', 'OANDA API'],
                    'technical_risks': [
                        'API rate limiting',
                        'Model retraining overhead',
                        'Data quality issues'
                    ],
                    'estimated_effort_hours': 80,
                    'current_status': 'concept'
                },
                'recruiter_email_automation': {
                    'description': 'Automated email outreach to recruiters',
                    'key_dependencies': ['smtplib', 'Anthropic API', 'Gmail API'],
                    'technical_risks': [
                        'Email deliverability',
                        'Anti-spam detection',
                        'Personalization quality'
                    ],
                    'estimated_effort_hours': 40,
                    'current_status': 'concept'
                }
            }

            normalized_name = project_name.lower().replace('-', '_')
            analysis = projects_db.get(normalized_name)

            if not analysis:
                # Generic analysis for unknown projects
                analysis = {
                    'description': f'Project: {project_name}',
                    'key_dependencies': ['TBD'],
                    'technical_risks': ['Unknown scope', 'Undefined requirements'],
                    'estimated_effort_hours': 100,
                    'current_status': 'unanalyzed'
                }

            return analysis

        except Exception as e:
            self.logger.error(f"[ANALYZE] Error analyzing {project_name}: {e}")
            return None

    def _calculate_feasibility(self, analysis: Dict[str, Any]) -> float:
        """Calculate feasibility score (0.0-1.0)."""
        try:
            score = 0.5  # Base score

            # Adjust based on effort (lower effort = higher score)
            effort = analysis.get('estimated_effort_hours', 100)
            if effort < 40:
                score += 0.3
            elif effort < 80:
                score += 0.15
            else:
                score -= 0.1

            # Adjust based on risks (fewer/lower risks = higher score)
            risks = analysis.get('technical_risks', [])
            risk_penalty = len(risks) * 0.05
            score -= risk_penalty

            # Clamp to [0.0, 1.0]
            return max(0.0, min(1.0, score))

        except Exception as e:
            self.logger.error(f"[CALC] Error calculating feasibility: {e}")
            return 0.5

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
