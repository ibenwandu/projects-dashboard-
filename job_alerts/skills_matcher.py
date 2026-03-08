import re
import logging
from typing import List, Dict, Tuple
from config import SKILLS_DATABASE, EXPERIENCE_LEVELS

class SkillsMatcher:
    def __init__(self, skills_database: Dict = None):
        self.skills_database = skills_database or SKILLS_DATABASE
        self.experience_levels = EXPERIENCE_LEVELS
        
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills mentioned in job description text"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_skills = []
        
        # Extract skills from each category
        for category, skills in self.skills_database.items():
            for skill in skills:
                # Check for exact matches and variations
                skill_patterns = [
                    skill.lower(),
                    skill.lower().replace(' ', ''),
                    skill.lower().replace(' ', '-'),
                    skill.lower().replace(' ', '_')
                ]
                
                for pattern in skill_patterns:
                    if pattern in text_lower:
                        found_skills.append(skill)
                        break
        
        # Remove duplicates while preserving order
        unique_skills = []
        for skill in found_skills:
            if skill not in unique_skills:
                unique_skills.append(skill)
        
        return unique_skills
    
    def determine_experience_level(self, text: str) -> str:
        """Determine experience level from job description"""
        if not text:
            return "Unknown"
        
        text_lower = text.lower()
        
        # Check for senior level indicators
        for indicator in self.experience_levels["senior"]:
            if indicator in text_lower:
                return "Senior"
        
        # Check for mid level indicators
        for indicator in self.experience_levels["mid"]:
            if indicator in text_lower:
                return "Mid Level"
        
        # Check for entry level indicators
        for indicator in self.experience_levels["entry"]:
            if indicator in text_lower:
                return "Entry Level"
        
        return "Unknown"
    
    def calculate_match_score(self, required_skills: List[str], user_skills: List[str] = None) -> float:
        """Calculate match score between required skills and user skills"""
        if not required_skills:
            return 0.0
        
        if not user_skills:
            # If no user skills provided, use all skills from database
            user_skills = []
            for skills in self.skills_database.values():
                user_skills.extend(skills)
        
        # Convert to lowercase for comparison
        required_lower = [skill.lower() for skill in required_skills]
        user_lower = [skill.lower() for skill in user_skills]
        
        # Count matches
        matches = 0
        for req_skill in required_lower:
            if req_skill in user_lower:
                matches += 1
        
        # Calculate score as percentage of required skills that match
        match_score = matches / len(required_skills) if required_skills else 0.0
        
        return round(match_score, 2)
    
    def get_skills_breakdown(self, required_skills: List[str]) -> Dict[str, List[str]]:
        """Break down required skills by category"""
        breakdown = {}
        
        for skill in required_skills:
            for category, skills in self.skills_database.items():
                if skill in skills:
                    if category not in breakdown:
                        breakdown[category] = []
                    breakdown[category].append(skill)
                    break
        
        return breakdown
    
    def analyze_job_description(self, job_description: str, user_skills: List[str] = None) -> Dict:
        """Complete analysis of a job description"""
        if not job_description:
            return {
                'skills_required': [],
                'skills_matched': [],
                'match_score': 0.0,
                'experience_level': 'Unknown',
                'skills_breakdown': {}
            }
        
        # Extract required skills
        required_skills = self.extract_skills_from_text(job_description)
        
        # Determine experience level
        experience_level = self.determine_experience_level(job_description)
        
        # Calculate match score
        match_score = self.calculate_match_score(required_skills, user_skills)
        
        # Get skills breakdown
        skills_breakdown = self.get_skills_breakdown(required_skills)
        
        # Determine which skills match user skills
        matched_skills = []
        if user_skills:
            user_lower = [skill.lower() for skill in user_skills]
            for skill in required_skills:
                if skill.lower() in user_lower:
                    matched_skills.append(skill)
        
        return {
            'skills_required': required_skills,
            'skills_matched': matched_skills,
            'match_score': match_score,
            'experience_level': experience_level,
            'skills_breakdown': skills_breakdown
        }
    
    def get_missing_skills(self, required_skills: List[str], user_skills: List[str]) -> List[str]:
        """Get skills that are required but not in user's skill set"""
        if not required_skills or not user_skills:
            return required_skills
        
        user_lower = [skill.lower() for skill in user_skills]
        missing = []
        
        for skill in required_skills:
            if skill.lower() not in user_lower:
                missing.append(skill)
        
        return missing
    
    def suggest_skill_improvements(self, job_analysis: Dict) -> Dict:
        """Suggest improvements based on job analysis"""
        suggestions = {
            'priority_skills': [],
            'learning_path': [],
            'match_improvement': 0.0
        }
        
        required_skills = job_analysis.get('skills_required', [])
        matched_skills = job_analysis.get('skills_matched', [])
        current_score = job_analysis.get('match_score', 0.0)
        
        # Find missing skills
        missing_skills = [skill for skill in required_skills if skill not in matched_skills]
        
        if missing_skills:
            # Prioritize skills by category (programming languages first, then frameworks, etc.)
            priority_order = ['programming_languages', 'frameworks', 'databases', 'cloud_platforms', 'tools', 'methodologies']
            
            for category in priority_order:
                category_skills = [skill for skill in missing_skills if skill in self.skills_database.get(category, [])]
                if category_skills:
                    suggestions['priority_skills'].extend(category_skills[:3])  # Top 3 from each category
            
            # Calculate potential improvement
            potential_matches = len(matched_skills) + len(missing_skills)
            if potential_matches > 0:
                suggestions['match_improvement'] = round(len(matched_skills) / potential_matches, 2)
        
        return suggestions
    
    def update_user_skills(self, new_skills: List[str], category: str = None):
        """Update the skills database with new user skills"""
        if category and category in self.skills_database:
            for skill in new_skills:
                if skill not in self.skills_database[category]:
                    self.skills_database[category].append(skill)
        else:
            # Add to programming_languages by default
            for skill in new_skills:
                if skill not in self.skills_database['programming_languages']:
                    self.skills_database['programming_languages'].append(skill)
        
        logging.info(f"Updated skills database with {len(new_skills)} new skills")
    
    def get_skills_summary(self) -> Dict:
        """Get summary of all skills in the database"""
        summary = {
            'total_skills': 0,
            'categories': {},
            'most_common': []
        }
        
        all_skills = []
        for category, skills in self.skills_database.items():
            summary['categories'][category] = len(skills)
            summary['total_skills'] += len(skills)
            all_skills.extend(skills)
        
        return summary
























