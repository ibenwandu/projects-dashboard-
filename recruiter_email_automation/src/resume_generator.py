"""Generate customized resumes from template, LinkedIn PDF, and skills file"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv

# Optional imports with fallbacks
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PyPDF2 not available. LinkedIn PDF extraction will be limited.")

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    print("Warning: pdfkit not available. Resumes will be saved as text files.")

load_dotenv()

class ResumeGenerator:
    """Generate customized resumes for recruiter emails"""
    
    def __init__(self):
        """Initialize resume generator"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in .env file")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Get project root directory (parent of src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # File paths - resolve relative to project root
        resume_template = os.getenv('RESUME_TEMPLATE_PATH', 'data/resume_template.txt')
        linkedin_pdf = os.getenv('LINKEDIN_PDF_PATH', 'data/linkedin.pdf')
        skills_summary = os.getenv('SKILLS_SUMMARY_PATH', 'data/skills_summary.txt')
        output_dir = 'output/resumes'
        
        # Make paths absolute if relative
        self.resume_template_path = os.path.join(project_root, resume_template) if not os.path.isabs(resume_template) else resume_template
        self.linkedin_pdf_path = os.path.join(project_root, linkedin_pdf) if not os.path.isabs(linkedin_pdf) else linkedin_pdf
        self.skills_summary_path = os.path.join(project_root, skills_summary) if not os.path.isabs(skills_summary) else skills_summary
        self.output_dir = os.path.join(project_root, output_dir) if not os.path.isabs(output_dir) else output_dir
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_resume(self, email: Dict[str, Any]) -> str:
        """
        Generate a customized resume based on the recruiter email
        
        Args:
            email: Recruiter email dictionary
            
        Returns:
            Path to generated resume PDF
        """
        try:
            # Load template and data
            template = self._load_resume_template()
            linkedin_data = self._extract_linkedin_data()
            skills_data = self._load_skills_summary()
            
            # Analyze job requirements from email
            job_requirements = self._extract_job_requirements(email)
            
            # Generate customized resume content
            resume_content = self._generate_customized_resume(
                template=template,
                linkedin_data=linkedin_data,
                skills_data=skills_data,
                job_requirements=job_requirements,
                email=email
            )
            
            # Save resume
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sender_domain = email.get('sender_email', 'unknown').split('@')[0]
            filename = f"resume_{sender_domain}_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            # Convert to PDF
            self._save_resume_pdf(resume_content, output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Error generating resume: {e}")
            # Return template path as fallback
            return self.resume_template_path
    
    def _load_resume_template(self) -> str:
        """Load resume template from file"""
        if os.path.exists(self.resume_template_path):
            with open(self.resume_template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Return default template structure
            return """
            RESUME TEMPLATE
            
            [Your Name]
            [Contact Information]
            
            PROFESSIONAL SUMMARY
            [Summary section]
            
            EXPERIENCE
            [Experience section]
            
            EDUCATION
            [Education section]
            
            SKILLS
            [Skills section]
            """
    
    def _extract_linkedin_data(self) -> str:
        """Extract text data from LinkedIn PDF"""
        if not os.path.exists(self.linkedin_pdf_path):
            return "LinkedIn profile data not available."
        
        if not PDF_AVAILABLE:
            return "LinkedIn PDF extraction not available (PyPDF2 not installed)."
        
        try:
            text = ""
            with open(self.linkedin_pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error extracting LinkedIn PDF: {e}")
            return "LinkedIn profile data extraction failed."
    
    def _load_skills_summary(self) -> str:
        """Load skills and projects summary"""
        if os.path.exists(self.skills_summary_path):
            with open(self.skills_summary_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Skills summary not available."
    
    def _extract_job_requirements(self, email: Dict[str, Any]) -> str:
        """Extract job requirements from recruiter email using AI"""
        try:
            prompt = f"""
            Analyze this recruiter email and extract:
            1. Job title/role mentioned
            2. Key skills/requirements mentioned
            3. Industry/domain
            4. Any specific qualifications needed
            
            Email Subject: {email.get('subject', '')}
            Email Content: {email.get('body', email.get('snippet', ''))[:2000]}
            
            Provide a concise summary of the job requirements.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a job requirements analyzer. Extract key requirements from recruiter emails."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error extracting job requirements: {e}")
            return "Job requirements analysis unavailable."
    
    def _generate_customized_resume(self, template: str, linkedin_data: str, 
                                   skills_data: str, job_requirements: str,
                                   email: Dict[str, Any]) -> str:
        """Generate customized resume content using AI"""
        try:
            prompt = f"""
            Create a professional, customized resume based on the following:
            
            RESUME TEMPLATE:
            {template}
            
            LINKEDIN PROFILE DATA:
            {linkedin_data[:2000]}
            
            SKILLS AND PROJECTS SUMMARY:
            {skills_data[:2000]}
            
            JOB REQUIREMENTS FROM RECRUITER EMAIL:
            {job_requirements}
            
            RECRUITER EMAIL CONTEXT:
            From: {email.get('sender_name', '')}
            Subject: {email.get('subject', '')}
            
            Instructions:
            1. Create a professional resume that highlights relevant experience and skills
            2. Emphasize qualifications that match the job requirements
            3. Maintain professional formatting
            4. Include all relevant sections: Professional Summary, Experience, Education, Skills
            5. Tailor the content to be relevant to the position mentioned in the email
            6. Keep it concise (1-2 pages when formatted)
            
            Generate the complete resume content in a clean, professional format.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional resume writer. Create customized, ATS-friendly resumes that highlight relevant qualifications."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating customized resume: {e}")
            return template  # Return template as fallback
    
    def _save_resume_pdf(self, content: str, output_path: str):
        """Save resume content as PDF"""
        try:
            # Try using pdfkit if available
            if PDFKIT_AVAILABLE:
                try:
                    # Convert markdown/text to HTML first
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            h1 {{ color: #333; border-bottom: 2px solid #333; }}
                            h2 {{ color: #555; margin-top: 20px; }}
                            p {{ margin: 10px 0; }}
                        </style>
                    </head>
                    <body>
                        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{content}</pre>
                    </body>
                    </html>
                    """
                    
                    pdfkit.from_string(html_content, output_path)
                    return
                except Exception as e:
                    print(f"PDF generation failed: {e}. Falling back to text file.")
            
            # Fallback: Save as text file
            output_path = output_path.replace('.pdf', '.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Saved resume as text file: {output_path}")
                
        except Exception as e:
            print(f"Error saving resume: {e}")
            # Save as text file as last resort
            output_path = output_path.replace('.pdf', '.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

