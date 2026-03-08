"""Generate professional responses to recruiter emails"""

import os
import openai
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ResponseGenerator:
    """Generate professional email responses for recruiter emails"""
    
    def __init__(self):
        """Initialize response generator"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in .env file")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    def generate_response(self, email: Dict[str, Any], resume_path: str = '') -> str:
        """
        Generate a professional response to a recruiter email
        
        Args:
            email: Recruiter email dictionary
            resume_path: Path to the generated resume (optional)
            
        Returns:
            Professional email response text
        """
        try:
            prompt = self._create_response_prompt(email, resume_path)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional email writer. Create polite, engaging, and professional responses to recruiter emails. Keep responses concise but warm."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating response: {e}")
            # Return default response
            return self._default_response(email)
    
    def _create_response_prompt(self, email: Dict[str, Any], resume_path: str) -> str:
        """Create prompt for response generation"""
        resume_note = ""
        if resume_path:
            resume_note = f"\nNote: A customized resume has been generated and is attached to this response."
        
        return f"""
        Generate a professional email response to this recruiter email:
        
        From: {email.get('sender_name', '')} <{email.get('sender_email', '')}>
        Subject: {email.get('subject', '')}
        Content: {email.get('body', email.get('snippet', ''))[:2000]}
        
        Requirements:
        1. Express genuine interest in the opportunity
        2. Be professional and courteous
        3. Mention that your resume is attached (if applicable)
        4. Show enthusiasm about the role/company
        5. Keep it concise (2-3 paragraphs maximum)
        6. Include a professional closing
        7. Do NOT include your email signature (that will be added separately)
        
        {resume_note}
        
        Generate the complete email response body (without subject line or signature).
        """
    
    def _default_response(self, email: Dict[str, Any]) -> str:
        """Default response template if AI generation fails"""
        return f"""Dear {email.get('sender_name', 'Recruiter')},

Thank you for reaching out regarding the opportunity you mentioned. I am very interested in learning more about this position and how my background might align with your needs.

I have attached my resume for your review. I would welcome the opportunity to discuss this role further and explore how I can contribute to your team.

Thank you for considering my application. I look forward to hearing from you.

Best regards"""



