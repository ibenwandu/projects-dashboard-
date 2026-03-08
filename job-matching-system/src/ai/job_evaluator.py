"""
AI-powered job evaluation using OpenAI or Claude API.
"""
import os
import logging
import re
import time
from typing import Dict, Any, Tuple, Optional
from openai import OpenAI
from anthropic import Anthropic
from .prompt_templates import JOB_EVALUATION_PROMPT, KEYWORD_OPTIMIZATION_PROMPT

logger = logging.getLogger(__name__)

class JobEvaluator:
    def __init__(self, openai_api_key: Optional[str] = None, claude_api_key: Optional[str] = None, 
                 rate_limit_delay: float = 2.0):
        self.openai_client = None
        self.claude_client = None
        self.rate_limit_delay = rate_limit_delay

        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized")

        if claude_api_key:
            self.claude_client = Anthropic(api_key=claude_api_key)
            logger.info("Claude client initialized")

        if not self.openai_client and not self.claude_client:
            raise ValueError("At least one AI API key must be provided")

    def evaluate_job_fit(self, job_data: Dict[str, Any], profile_summary: str) -> Tuple[int, str]:
        """
        Evaluate how well a job fits the candidate profile.

        Returns:
            Tuple of (score, reasoning)
        """
        prompt = JOB_EVALUATION_PROMPT.format(
            profile_summary=profile_summary,
            job_title=job_data.get('title', ''),
            company=job_data.get('company', ''),
            location=job_data.get('location', ''),
            job_description=job_data.get('description', '')[:3000]  # Limit description length
        )

        try:
            response = self._get_ai_response(prompt)
            return self._parse_evaluation_response(response)

        except Exception as e:
            logger.error(f"Error evaluating job fit: {e}")
            return 0, f"Error during evaluation: {str(e)}"

    def extract_keywords(self, job_description: str) -> Dict[str, list]:
        """Extract keywords from job description for ATS optimization."""
        prompt = KEYWORD_OPTIMIZATION_PROMPT.format(job_description=job_description)

        try:
            response = self._get_ai_response(prompt)
            return self._parse_keywords_response(response)

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return {
                'MUST-HAVE SKILLS': [],
                'PREFERRED SKILLS': [],
                'INDUSTRY TERMS': [],
                'SOFT SKILLS': [],
                'TOOLS/TECHNOLOGIES': [],
                'QUALIFICATIONS': []
            }

    def _get_ai_response(self, prompt: str) -> str:
        """Get response from available AI service with rate limiting."""
        # Add delay to prevent rate limiting
        time.sleep(self.rate_limit_delay)  # Configurable delay between API calls
        
        # Try OpenAI first if available
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,
                    temperature=0.3
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}")
                if not self.claude_client:
                    raise e

        # Try Claude if OpenAI failed or not available
        if self.claude_client:
            try:
                response = self.claude_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            except Exception as e:
                logger.error(f"Claude API failed: {e}")
                raise e

        raise Exception("No AI service available")

    def _parse_evaluation_response(self, response: str) -> Tuple[int, str]:
        """Parse the AI evaluation response to extract score and reasoning."""
        try:
            lines = response.strip().split('\n')
            score = 0
            reasoning = ""

            for line in lines:
                line = line.strip()
                if line.startswith('SCORE:'):
                    score_text = line.replace('SCORE:', '').strip()
                    # Extract number from score text
                    score_match = re.search(r'\d+', score_text)
                    if score_match:
                        score = int(score_match.group())
                        score = max(1, min(100, score))  # Clamp between 1-100

                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
                    # Continue reading subsequent lines as part of reasoning
                    continue
                elif reasoning and line and not line.startswith(('SCORE:', 'REASONING:')):
                    reasoning += ' ' + line

            if not reasoning:
                reasoning = "No specific reasoning provided."

            return score, reasoning

        except Exception as e:
            logger.error(f"Error parsing evaluation response: {e}")
            return 0, f"Error parsing response: {str(e)}"

    def _parse_keywords_response(self, response: str) -> Dict[str, list]:
        """Parse the AI keywords extraction response."""
        keywords = {
            'MUST-HAVE SKILLS': [],
            'PREFERRED SKILLS': [],
            'INDUSTRY TERMS': [],
            'SOFT SKILLS': [],
            'TOOLS/TECHNOLOGIES': [],
            'QUALIFICATIONS': []
        }

        try:
            lines = response.strip().split('\n')
            current_category = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if line is a category header
                for category in keywords.keys():
                    if line.startswith(f'{category}:'):
                        current_category = category
                        # Extract keywords from the same line if present
                        keywords_part = line.replace(f'{category}:', '').strip()
                        if keywords_part:
                            keywords[category] = [k.strip() for k in keywords_part.split(',') if k.strip()]
                        break
                else:
                    # If we have a current category and this isn't a category header
                    if current_category and ':' not in line:
                        # This line contains additional keywords for the current category
                        additional_keywords = [k.strip() for k in line.split(',') if k.strip()]
                        keywords[current_category].extend(additional_keywords)

            # Clean up empty strings and duplicates
            for category in keywords:
                keywords[category] = list(set([k for k in keywords[category] if k]))

            logger.info(f"Extracted keywords: {sum(len(v) for v in keywords.values())} total")

        except Exception as e:
            logger.error(f"Error parsing keywords response: {e}")

        return keywords