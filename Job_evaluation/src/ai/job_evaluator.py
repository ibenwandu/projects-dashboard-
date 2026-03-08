import logging
import json
from typing import Dict, List, Optional, Tuple
import openai
import anthropic
from src.config import Config
from src.ai.prompt_templates import JobEvaluationPrompts

class JobEvaluator:
    """AI-powered job evaluation and scoring system"""
    
    def __init__(self):
        self.config = Config()
        self.prompts = JobEvaluationPrompts()
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI clients
        if self.config.OPENAI_API_KEY:
            openai.api_key = self.config.OPENAI_API_KEY
        
        if self.config.CLAUDE_API_KEY:
            self.claude_client = anthropic.Anthropic(api_key=self.config.CLAUDE_API_KEY)
    
    def evaluate_job_batch(self, jobs: List[Dict], profile_data: Dict) -> List[Dict]:
        """Evaluate a batch of jobs against user profile"""
        evaluated_jobs = []
        
        for job in jobs:
            try:
                evaluation = self.evaluate_single_job(job, profile_data)
                if evaluation:
                    # Merge job data with evaluation
                    evaluated_job = {**job, **evaluation}
                    evaluated_jobs.append(evaluated_job)
                    
            except Exception as e:
                self.logger.error(f"Error evaluating job {job.get('title', 'unknown')}: {str(e)}")
                # Add job with default low score if evaluation fails
                evaluated_job = job.copy()
                evaluated_job.update({
                    'match_score': 0,
                    'evaluation_status': 'failed',
                    'evaluation_error': str(e),
                    'feedback': 'Evaluation failed due to technical error'
                })
                evaluated_jobs.append(evaluated_job)
        
        self.logger.info(f"Evaluated {len(evaluated_jobs)} jobs")
        return evaluated_jobs
    
    def evaluate_single_job(self, job: Dict, profile_data: Dict) -> Optional[Dict]:
        """Evaluate a single job against user profile"""
        try:
            # Try Claude first, fallback to OpenAI
            if self.config.CLAUDE_API_KEY:
                return self._evaluate_with_claude(job, profile_data)
            elif self.config.OPENAI_API_KEY:
                return self._evaluate_with_openai(job, profile_data)
            else:
                raise Exception("No AI API keys configured")
                
        except Exception as e:
            self.logger.error(f"Error in single job evaluation: {str(e)}")
            return None
    
    def _evaluate_with_claude(self, job: Dict, profile_data: Dict) -> Dict:
        """Evaluate job using Claude API"""
        try:
            # Prepare the evaluation prompt
            prompt = self.prompts.get_job_evaluation_prompt(job, profile_data)
            
            # Call Claude API
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse response
            response_text = response.content[0].text
            return self._parse_evaluation_response(response_text)
            
        except Exception as e:
            self.logger.error(f"Claude API error: {str(e)}")
            raise
    
    def _evaluate_with_openai(self, job: Dict, profile_data: Dict) -> Dict:
        """Evaluate job using OpenAI API"""
        try:
            # Prepare the evaluation prompt
            prompt = self.prompts.get_job_evaluation_prompt(job, profile_data)
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=1000,
                temperature=0.1
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            return self._parse_evaluation_response(response_text)
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _parse_evaluation_response(self, response_text: str) -> Dict:
        """Parse AI evaluation response into structured data"""
        try:
            # Try to extract JSON from response
            if '{' in response_text and '}' in response_text:
                # Find JSON content
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                
                evaluation_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['match_score', 'feedback']
                for field in required_fields:
                    if field not in evaluation_data:
                        raise ValueError(f"Missing required field: {field}")
                
                # Ensure score is within valid range
                score = evaluation_data.get('match_score', 0)
                if not isinstance(score, (int, float)) or score < 0 or score > 100:
                    evaluation_data['match_score'] = 0
                
                return evaluation_data
            
            else:
                # Fallback: extract score and use full text as feedback
                score = self._extract_score_from_text(response_text)
                return {
                    'match_score': score,
                    'feedback': response_text.strip(),
                    'skills_match': 'Unknown',
                    'experience_match': 'Unknown',
                    'education_match': 'Unknown'
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing evaluation response: {str(e)}")
            # Return default evaluation
            return {
                'match_score': 0,
                'feedback': 'Failed to parse evaluation response',
                'evaluation_status': 'parse_error',
                'skills_match': 'Unknown',
                'experience_match': 'Unknown',
                'education_match': 'Unknown'
            }
    
    def _extract_score_from_text(self, text: str) -> int:
        """Extract numerical score from text response"""
        import re
        
        # Look for patterns like "Score: 85", "85/100", "Rating: 7.5/10"
        patterns = [
            r'score:?\s*(\d+)',
            r'rating:?\s*(\d+(?:\.\d+)?)',
            r'(\d+)/100',
            r'(\d+)%',
            r'match:?\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                score = float(match.group(1))
                # Convert to 100-point scale if needed
                if score <= 10:  # Assume 10-point scale
                    score *= 10
                return min(100, max(0, int(score)))
        
        # Default score if no pattern found
        return 50
    
    def generate_detailed_feedback(self, job: Dict, profile_data: Dict, score: int) -> str:
        """Generate detailed feedback for job evaluation"""
        try:
            feedback_prompt = self.prompts.get_detailed_feedback_prompt(job, profile_data, score)
            
            if self.config.CLAUDE_API_KEY:
                response = self.claude_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=500,
                    messages=[{
                        "role": "user",
                        "content": feedback_prompt
                    }]
                )
                return response.content[0].text
            
            elif self.config.OPENAI_API_KEY:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{
                        "role": "user",
                        "content": feedback_prompt
                    }],
                    max_tokens=500,
                    temperature=0.3
                )
                return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating detailed feedback: {str(e)}")
        
        return f"Job evaluation completed with a match score of {score}/100."
    
    def filter_high_scoring_jobs(self, evaluated_jobs: List[Dict], 
                               min_score: int = None) -> List[Dict]:
        """Filter jobs that meet minimum score threshold"""
        min_score = min_score or self.config.MIN_MATCH_SCORE
        
        high_scoring_jobs = [
            job for job in evaluated_jobs 
            if job.get('match_score', 0) >= min_score
        ]
        
        # Sort by score (highest first)
        high_scoring_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        self.logger.info(f"Found {len(high_scoring_jobs)} jobs with score >= {min_score}")
        return high_scoring_jobs
    
    def get_evaluation_summary(self, evaluated_jobs: List[Dict]) -> Dict:
        """Generate summary statistics for job evaluations"""
        if not evaluated_jobs:
            return {
                'total_jobs': 0,
                'average_score': 0,
                'high_scoring_count': 0,
                'score_distribution': {}
            }
        
        scores = [job.get('match_score', 0) for job in evaluated_jobs]
        
        summary = {
            'total_jobs': len(evaluated_jobs),
            'average_score': sum(scores) / len(scores),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'high_scoring_count': len([s for s in scores if s >= self.config.MIN_MATCH_SCORE]),
            'score_distribution': self._get_score_distribution(scores)
        }
        
        return summary
    
    def _get_score_distribution(self, scores: List[int]) -> Dict:
        """Get distribution of scores by ranges"""
        ranges = {
            '90-100': 0,
            '80-89': 0,
            '70-79': 0,
            '60-69': 0,
            '50-59': 0,
            '0-49': 0
        }
        
        for score in scores:
            if score >= 90:
                ranges['90-100'] += 1
            elif score >= 80:
                ranges['80-89'] += 1
            elif score >= 70:
                ranges['70-79'] += 1
            elif score >= 60:
                ranges['60-69'] += 1
            elif score >= 50:
                ranges['50-59'] += 1
            else:
                ranges['0-49'] += 1
        
        return ranges