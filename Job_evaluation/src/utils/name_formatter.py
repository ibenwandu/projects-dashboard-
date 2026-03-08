import re
import unicodedata
from typing import Optional

class NameFormatter:
    """Utility class for standardized file naming conventions"""
    
    @staticmethod
    def format_job_filename(company: str, job_title: str, file_type: str = "docx") -> str:
        """Format filename as CompanyName_JobTitle.extension"""
        
        # Clean company name
        clean_company = NameFormatter.clean_name_part(company)
        
        # Clean job title
        clean_title = NameFormatter.clean_name_part(job_title)
        
        # Combine and ensure reasonable length
        filename = f"{clean_company}_{clean_title}"
        
        # Limit filename length (Windows has 260 char path limit)
        if len(filename) > 100:
            # Truncate but keep both parts
            half_length = 47  # Leave room for underscore and extension
            clean_company = clean_company[:half_length]
            clean_title = clean_title[:half_length]
            filename = f"{clean_company}_{clean_title}"
        
        return f"{filename}.{file_type}"
    
    @staticmethod
    def clean_name_part(name: str) -> str:
        """Clean a name part for use in filename"""
        if not name:
            return "Unknown"
        
        # Normalize unicode characters
        name = unicodedata.normalize('NFKD', name)
        
        # Remove or replace problematic characters
        # Replace spaces and common separators with underscores
        name = re.sub(r'[\s\-\–\—\/\\]+', '_', name)
        
        # Remove or replace invalid filename characters
        name = re.sub(r'[<>:"/\\|?*&%#@!]', '', name)
        
        # Remove parentheses and their contents
        name = re.sub(r'\([^)]*\)', '', name)
        
        # Replace multiple underscores with single
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Convert to title case for consistency
        name = name.title()
        
        # Handle empty result
        if not name:
            return "Unknown"
        
        return name
    
    @staticmethod
    def format_resume_filename(company: str, job_title: str, 
                             candidate_name: str = "Resume") -> str:
        """Format resume filename with candidate info"""
        base_name = NameFormatter.format_job_filename(company, job_title, "docx")
        
        # Remove extension and add candidate name
        base_without_ext = base_name.rsplit('.', 1)[0]
        clean_candidate = NameFormatter.clean_name_part(candidate_name)
        
        return f"{clean_candidate}_{base_without_ext}.docx"
    
    @staticmethod
    def format_feedback_filename(company: str, job_title: str) -> str:
        """Format feedback filename"""
        base_name = NameFormatter.format_job_filename(company, job_title, "docx")
        base_without_ext = base_name.rsplit('.', 1)[0]
        
        return f"Feedback_{base_without_ext}.docx"
    
    @staticmethod
    def extract_company_from_filename(filename: str) -> Optional[str]:
        """Extract company name from standardized filename"""
        try:
            # Remove file extension
            name_without_ext = filename.rsplit('.', 1)[0]
            
            # Split on underscore and take first part
            parts = name_without_ext.split('_')
            if len(parts) >= 2:
                return parts[0]
            
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def extract_job_title_from_filename(filename: str) -> Optional[str]:
        """Extract job title from standardized filename"""
        try:
            # Remove file extension
            name_without_ext = filename.rsplit('.', 1)[0]
            
            # Split on underscore and take second part
            parts = name_without_ext.split('_')
            if len(parts) >= 2:
                return parts[1]
            
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate that filename follows conventions"""
        try:
            # Check basic format
            if not filename or '.' not in filename:
                return False
            
            name_part = filename.rsplit('.', 1)[0]
            
            # Should contain at least one underscore
            if '_' not in name_part:
                return False
            
            # Should not contain invalid characters
            invalid_chars = r'[<>:"/\\|?*]'
            if re.search(invalid_chars, filename):
                return False
            
            # Should not be too long
            if len(filename) > 150:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def suggest_filename_fix(original_filename: str, company: str, 
                           job_title: str) -> str:
        """Suggest a fixed filename if original doesn't follow conventions"""
        
        if NameFormatter.validate_filename(original_filename):
            return original_filename
        
        # Extract file extension if present
        extension = "docx"
        if '.' in original_filename:
            extension = original_filename.rsplit('.', 1)[1]
        
        # Generate new filename using conventions
        return NameFormatter.format_job_filename(company, job_title, extension)