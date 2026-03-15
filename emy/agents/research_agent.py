"""
ResearchAgent - evaluates new projects and topics for feasibility.

Provides AI-powered analysis via Claude API.
"""

import logging
from datetime import datetime
from typing import Tuple, Dict, Any

from emy.agents.base_agent import EMySubAgent

logger = logging.getLogger('ResearchAgent')


class ResearchAgent(EMySubAgent):
    """Agent for researching and evaluating projects and topics."""

    def __init__(self):
        """Initialize ResearchAgent."""
        super().__init__('ResearchAgent', 'claude-haiku-4-5-20251001')

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute research agent.

        Analyzes research topics and generates feasibility analysis using Claude.

        Returns:
            (True, {"response": analysis, "timestamp": iso_time, "agent": "ResearchAgent"})
            (False, {"error": error_message})
        """
        try:
            if self.check_disabled():
                self.logger.warning("ResearchAgent disabled")
                return (False, {'reason': 'disabled'})

            # Build research prompt
            prompt = self._build_research_prompt()

            # Get Claude analysis
            response = self._call_claude(prompt, max_tokens=2048)

            result = {
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "agent": self.agent_name
            }

            self.logger.info(f"ResearchAgent completed ({len(response)} chars)")
            return (True, result)

        except Exception as e:
            error_msg = f"ResearchAgent error: {e}"
            self.logger.error(error_msg)
            return (False, {"error": error_msg})

    async def send_feasibility_assessment(self, opportunity: dict, assessment: str, recommendation: str) -> bool:
        """Send feasibility assessment email.

        Args:
            opportunity: Dict with 'contact_name', 'title', 'email'
            assessment: Assessment text
            recommendation: Recommendation text

        Returns:
            True if send succeeded, False otherwise
        """
        context = {
            'recipient_name': opportunity.get('contact_name', 'Valued Contact'),
            'opportunity': opportunity.get('title', 'Opportunity'),
            'assessment': assessment,
            'recommendation': recommendation,
            'next_steps': self._generate_next_steps(opportunity)
        }

        html_body = await self.email_client.render_template('emails/feasibility_assessment.jinja2', context)

        result = await self.email_client.send(
            to=opportunity.get('email', ''),
            subject=f"Feasibility Assessment: {opportunity.get('title', 'Opportunity')}",
            body=html_body,
            html=True
        )

        return result

    def _generate_next_steps(self, opportunity: dict) -> list:
        """Generate next steps based on opportunity."""
        return [
            "Review detailed market analysis",
            "Schedule stakeholder discussion",
            "Develop implementation timeline"
        ]

    def _build_research_prompt(self) -> str:
        """Build research analysis prompt."""
        return """You are Ibe's AI Chief of Staff (Emy).

Your role: Evaluate projects, research topics, and provide feasibility analysis.

Current request: Analyze the current Emy project portfolio and identify:
1. Top research priorities (2-3 items)
2. Technical feasibility assessment for each
3. Estimated complexity (Low/Medium/High)
4. Key risks and dependencies
5. Recommended next steps

Provide concise, actionable analysis in 200-300 words or less."""
