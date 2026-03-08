"""Email classification using AI to identify recruiter, task, and other emails"""

import os
import json
import openai
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class EmailClassifier:
    """Classify emails into recruiter, task, or other categories"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in .env file")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    def classify_email(self, email: Dict[str, Any]) -> str:
        """
        Classify email as 'recruiter', 'task', or 'other'
        
        Returns:
            'recruiter': Email from a recruiter
            'task': Email requiring action/task (non-recruiter)
            'other': All other emails
        """
        try:
            prompt = self._create_classification_prompt(email)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an email classification assistant. Classify emails into exactly one category: 'recruiter', 'task', or 'other'. Respond only with valid JSON in this format: {\"category\": \"recruiter\"|\"task\"|\"other\", \"confidence\": \"high\"|\"medium\"|\"low\", \"reason\": \"brief explanation\"}"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            # Try to parse JSON response
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            category = result.get('category', 'other').lower()
            
            # Validate category
            if category not in ['recruiter', 'task', 'other']:
                category = 'other'
            
            return category
            
        except Exception as e:
            print(f"Error classifying email: {e}")
            # Default to 'other' if classification fails
            return 'other'
    
    def _create_classification_prompt(self, email: Dict[str, Any]) -> str:
        """Create prompt for email classification"""
        return f"""
        Classify this email into exactly one category:
        
        From: {email.get('sender_name', '')} <{email.get('sender_email', '')}>
        Subject: {email.get('subject', '')}
        Content: {email.get('body', email.get('snippet', ''))[:1000]}
        
        Categories:
        1. "recruiter" - Emails from recruiters, headhunters, talent acquisition, HR professionals, or job-related opportunities
        2. "task" - Emails that require you to perform an action, task, or respond (but NOT from recruiters). Examples:
           - Meeting requests
           - Questions needing answers
           - Tasks or assignments
           - Requests for information
           - Deadlines or approvals needed
        3. "other" - All other emails (newsletters, notifications, FYI emails, etc.)
        
        Respond with JSON format:
        {{
            "category": "recruiter" | "task" | "other",
            "confidence": "high" | "medium" | "low",
            "reason": "brief explanation"
        }}
        """
    
    def summarize_task_email(self, email: Dict[str, Any]) -> str:
        """
        Generate a 3-sentence summary for task emails
        
        Args:
            email: Email dictionary
            
        Returns:
            Three-sentence summary string
        """
        try:
            prompt = f"""
            Summarize this email in exactly 3 sentences. Focus on:
            1. What action or task is required
            2. Any deadlines or urgency
            3. Key details needed to complete the task
            
            From: {email.get('sender_name', '')} <{email.get('sender_email', '')}>
            Subject: {email.get('subject', '')}
            Content: {email.get('body', email.get('snippet', ''))[:1500]}
            
            Provide only the 3-sentence summary, no additional text.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a concise email summarizer. Provide exactly 3 sentences summarizing the task or action required."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            print(f"Error summarizing task email: {e}")
            # Fallback summary
            return f"Email from {email.get('sender_name', 'Unknown')} regarding '{email.get('subject', 'No subject')}'. Review required."

