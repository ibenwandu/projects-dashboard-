"""
Profile manager for loading and managing user profile data.
"""
import os
import logging
from typing import Dict, Any, Optional
from .google_drive_client import GoogleDriveClient

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, drive_client: GoogleDriveClient, 
                 linkedin_pdf_id: str, summary_txt_id: str):
        self.drive_client = drive_client
        self.linkedin_pdf_id = linkedin_pdf_id
        self.summary_txt_id = summary_txt_id
        self._profile_cache = {}
    
    def load_profile(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load complete user profile from Google Drive."""
        if not force_refresh and self._profile_cache:
            logger.info("Using cached profile data")
            return self._profile_cache
        
        profile = {
            'linkedin_content': '',
            'summary': '',
            'skills': [],
            'experience': [],
            'education': []
        }
        
        # Load LinkedIn PDF
        linkedin_text = self.drive_client.extract_pdf_text(self.linkedin_pdf_id)
        if linkedin_text:
            profile['linkedin_content'] = linkedin_text
            profile.update(self._parse_linkedin_profile(linkedin_text))
            logger.info("LinkedIn profile loaded successfully")
        else:
            logger.warning("Failed to load LinkedIn profile")
        
        # Load summary text
        summary_text = self.drive_client.download_text_file(self.summary_txt_id)
        if summary_text:
            profile['summary'] = summary_text.strip()
            logger.info("Professional summary loaded successfully")
        else:
            logger.warning("Failed to load professional summary")
        
        self._profile_cache = profile
        return profile
    
    def _parse_linkedin_profile(self, linkedin_text: str) -> Dict[str, Any]:
        """Parse LinkedIn profile text to extract structured data."""
        parsed_data = {
            'skills': [],
            'experience': [],
            'education': []
        }
        
        try:
            lines = linkedin_text.split('\n')
            current_section = None
            current_item = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if 'skills' in line.lower() and len(line) < 50:
                    current_section = 'skills'
                    continue
                elif 'experience' in line.lower() and len(line) < 50:
                    current_section = 'experience'
                    continue
                elif 'education' in line.lower() and len(line) < 50:
                    current_section = 'education'
                    continue
                
                # Parse based on current section
                if current_section == 'skills':
                    # Skills are usually listed as bullet points or comma-separated
                    if '•' in line or '·' in line:
                        skill = line.replace('•', '').replace('·', '').strip()
                        if skill:
                            parsed_data['skills'].append(skill)
                    elif ',' in line:
                        skills = [s.strip() for s in line.split(',')]
                        parsed_data['skills'].extend([s for s in skills if s])
                    else:
                        if line and len(line) < 100:  # Reasonable skill length
                            parsed_data['skills'].append(line)
                
                elif current_section == 'experience':
                    # Experience parsing (simplified)
                    if any(keyword in line.lower() for keyword in ['analyst', 'manager', 'coordinator', 'specialist']):
                        if current_item:
                            parsed_data['experience'].append(current_item)
                        current_item = {'title': line, 'description': ''}
                    elif current_item:
                        current_item['description'] += ' ' + line
                
                elif current_section == 'education':
                    # Education parsing (simplified)
                    if any(keyword in line.lower() for keyword in ['university', 'college', 'degree', 'bachelor', 'master']):
                        parsed_data['education'].append(line)
            
            # Add last experience item
            if current_item and current_section == 'experience':
                parsed_data['experience'].append(current_item)
            
            # Clean up skills list
            parsed_data['skills'] = list(set([
                skill.strip() for skill in parsed_data['skills'] 
                if skill.strip() and len(skill.strip()) > 2
            ]))
            
            logger.info(f"Parsed LinkedIn profile: {len(parsed_data['skills'])} skills, "
                       f"{len(parsed_data['experience'])} experiences, "
                       f"{len(parsed_data['education'])} education entries")
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn profile: {e}")
        
        return parsed_data
    
    def get_profile_summary(self) -> str:
        """Get a formatted profile summary for AI analysis."""
        profile = self.load_profile()
        
        summary_parts = []
        
        if profile.get('summary'):
            summary_parts.append(f"Professional Summary:\n{profile['summary']}")
        
        if profile.get('skills'):
            skills_str = ', '.join(profile['skills'][:20])  # Top 20 skills
            summary_parts.append(f"Key Skills: {skills_str}")
        
        if profile.get('experience'):
            exp_summaries = []
            for exp in profile['experience'][:5]:  # Top 5 experiences
                if isinstance(exp, dict):
                    title = exp.get('title', '')
                    desc = exp.get('description', '')[:200]  # First 200 chars
                    exp_summaries.append(f"- {title}: {desc}")
                else:
                    exp_summaries.append(f"- {str(exp)[:200]}")
            
            if exp_summaries:
                summary_parts.append("Recent Experience:\n" + '\n'.join(exp_summaries))
        
        if profile.get('education'):
            edu_str = '; '.join([str(edu)[:100] for edu in profile['education'][:3]])
            summary_parts.append(f"Education: {edu_str}")
        
        return '\n\n'.join(summary_parts)
    
    def refresh_profile(self):
        """Force refresh of profile data."""
        logger.info("Refreshing profile data from Google Drive")
        self.load_profile(force_refresh=True)