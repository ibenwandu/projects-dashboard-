"""
AI-powered resume builder for generating custom resumes.
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from anthropic import Anthropic
from src.ai.prompt_templates import RESUME_CUSTOMIZATION_PROMPT

logger = logging.getLogger(__name__)

class ResumeBuilder:
    def __init__(self, openai_api_key: Optional[str] = None, claude_api_key: Optional[str] = None):
        self.openai_client = None
        self.claude_client = None
        
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized for resume building")
        
        if claude_api_key:
            self.claude_client = Anthropic(api_key=claude_api_key)
            logger.info("Claude client initialized for resume building")
        
        if not self.openai_client and not self.claude_client:
            raise ValueError("At least one AI API key must be provided")
    
    def generate_custom_resume(self, profile_summary: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a custom resume tailored to a specific job.
        
        Args:
            profile_summary: Complete profile summary from ProfileManager
            job_data: Job information including title, company, description
            
        Returns:
            Dictionary containing resume sections and metadata
        """
        try:
            prompt = RESUME_CUSTOMIZATION_PROMPT.format(
                profile_summary=profile_summary,
                job_title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                job_description=job_data.get('description', '')[:4000]  # Limit description length
            )
            
            response = self._get_ai_response(prompt)
            parsed_resume = self._parse_resume_response(response)
            
            # Add metadata
            parsed_resume['metadata'] = {
                'job_title': job_data.get('title', ''),
                'company': job_data.get('company', ''),
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'target_job_url': job_data.get('application_link', ''),
                'match_score': job_data.get('score', 0)
            }
            
            logger.info(f"Custom resume generated for {job_data.get('title', '')} at {job_data.get('company', '')}")
            return parsed_resume
            
        except Exception as e:
            logger.error(f"Error generating custom resume: {e}")
            return self._create_fallback_resume(profile_summary, job_data)
    
    def _get_ai_response(self, prompt: str) -> str:
        """Get response from available AI service."""
        # Try OpenAI first if available
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.4
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
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            except Exception as e:
                logger.error(f"Claude API failed: {e}")
                raise e
        
        raise Exception("No AI service available")
    
    def _parse_resume_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI resume response into structured sections."""
        resume_sections = {
            'professional_summary': '',
            'core_competencies': [],
            'professional_experience': '',
            'education': '',
            'additional_sections': ''
        }
        
        try:
            lines = response.strip().split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify section headers
                if line.upper().startswith('PROFESSIONAL SUMMARY:'):
                    if current_section and current_content:
                        resume_sections[current_section] = '\n'.join(current_content)
                    current_section = 'professional_summary'
                    current_content = []
                    # Add content from the same line if present
                    content_part = line.split(':', 1)[1].strip()
                    if content_part:
                        current_content.append(content_part)
                
                elif line.upper().startswith('CORE COMPETENCIES:'):
                    if current_section and current_content:
                        resume_sections[current_section] = '\n'.join(current_content)
                    current_section = 'core_competencies'
                    current_content = []
                    content_part = line.split(':', 1)[1].strip()
                    if content_part:
                        current_content.append(content_part)
                
                elif line.upper().startswith('PROFESSIONAL EXPERIENCE:'):
                    if current_section and current_content:
                        if current_section == 'core_competencies':
                            # Parse competencies as list
                            competencies_text = '\n'.join(current_content)
                            resume_sections[current_section] = self._parse_competencies(competencies_text)
                        else:
                            resume_sections[current_section] = '\n'.join(current_content)
                    current_section = 'professional_experience'
                    current_content = []
                    content_part = line.split(':', 1)[1].strip()
                    if content_part:
                        current_content.append(content_part)
                
                elif line.upper().startswith('EDUCATION:'):
                    if current_section and current_content:
                        if current_section == 'core_competencies':
                            competencies_text = '\n'.join(current_content)
                            resume_sections[current_section] = self._parse_competencies(competencies_text)
                        else:
                            resume_sections[current_section] = '\n'.join(current_content)
                    current_section = 'education'
                    current_content = []
                    content_part = line.split(':', 1)[1].strip()
                    if content_part:
                        current_content.append(content_part)
                
                elif line.upper().startswith('ADDITIONAL SECTIONS:'):
                    if current_section and current_content:
                        if current_section == 'core_competencies':
                            competencies_text = '\n'.join(current_content)
                            resume_sections[current_section] = self._parse_competencies(competencies_text)
                        else:
                            resume_sections[current_section] = '\n'.join(current_content)
                    current_section = 'additional_sections'
                    current_content = []
                    content_part = line.split(':', 1)[1].strip()
                    if content_part:
                        current_content.append(content_part)
                
                else:
                    # Regular content line
                    if current_section:
                        current_content.append(line)
            
            # Handle the last section
            if current_section and current_content:
                if current_section == 'core_competencies':
                    competencies_text = '\n'.join(current_content)
                    resume_sections[current_section] = self._parse_competencies(competencies_text)
                else:
                    resume_sections[current_section] = '\n'.join(current_content)
            
            logger.info("Resume response parsed successfully")
            
        except Exception as e:
            logger.error(f"Error parsing resume response: {e}")
            # Return basic structure with raw response
            resume_sections['raw_response'] = response
        
        return resume_sections
    
    def _parse_competencies(self, competencies_text: str) -> list:
        """Parse core competencies text into a list."""
        competencies = []
        
        for line in competencies_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Remove bullet points and clean up
            line = line.replace('•', '').replace('-', '').replace('*', '').strip()
            
            if line:
                # Split on commas if multiple competencies in one line
                if ',' in line:
                    competencies.extend([comp.strip() for comp in line.split(',') if comp.strip()])
                else:
                    competencies.append(line)
        
        return competencies
    
    def _create_fallback_resume(self, profile_summary: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic resume structure when AI fails."""
        logger.warning("Creating fallback resume due to AI generation failure")
        
        return {
            'professional_summary': f"Experienced professional seeking opportunities in {job_data.get('title', 'the desired role')}.",
            'core_competencies': ['Leadership', 'Problem Solving', 'Communication', 'Project Management'],
            'professional_experience': 'Please refer to LinkedIn profile for detailed experience.',
            'education': 'Please refer to LinkedIn profile for education details.',
            'additional_sections': '',
            'metadata': {
                'job_title': job_data.get('title', ''),
                'company': job_data.get('company', ''),
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'target_job_url': job_data.get('application_link', ''),
                'match_score': job_data.get('score', 0),
                'fallback': True
            },
            'raw_response': 'Fallback resume - AI generation failed'
        }