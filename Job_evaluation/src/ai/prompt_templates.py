from typing import Dict, List

class JobEvaluationPrompts:
    """Prompt templates for AI job evaluation"""
    
    def get_job_evaluation_prompt(self, job: Dict, profile_data: Dict) -> str:
        """Get comprehensive job evaluation prompt"""
        
        job_title = job.get('title', 'N/A')
        job_company = job.get('company', 'N/A')
        job_location = job.get('location', 'N/A')
        job_description = job.get('description', '')
        job_url = job.get('url', '')
        
        linkedin_profile = profile_data.get('linkedin_pdf', '')
        summary = profile_data.get('summary_txt', '')
        
        prompt = f"""
You are an expert career advisor and job matching specialist. Please evaluate how well this job opportunity matches the candidate's profile.

**CANDIDATE PROFILE:**
LinkedIn Profile Summary: {linkedin_profile[:1000] if linkedin_profile else 'Not available'}

Professional Summary: {summary[:500] if summary else 'Not available'}

**JOB OPPORTUNITY:**
Title: {job_title}
Company: {job_company}
Location: {job_location}
Description: {job_description[:1000] if job_description else 'Limited description available'}
URL: {job_url}

**EVALUATION CRITERIA:**
Please evaluate this job match on a scale of 1-100 based on:

1. **Skills Alignment (40%)**: How well do the candidate's skills match the job requirements?
2. **Experience Relevance (30%)**: Is the candidate's experience level and background relevant?
3. **Industry/Domain Match (15%)**: Does the industry/domain align with candidate's background?
4. **Location/Remote Flexibility (10%)**: Does the location work for the candidate?
5. **Career Growth Potential (5%)**: Does this role offer advancement opportunities?

**RESPONSE FORMAT:**
Please respond with a JSON object containing:

{{
    "match_score": [integer from 1-100],
    "skills_match": "[Excellent/Good/Fair/Poor]",
    "experience_match": "[Excellent/Good/Fair/Poor]", 
    "education_match": "[Excellent/Good/Fair/Poor]",
    "location_suitability": "[Excellent/Good/Fair/Poor]",
    "industry_alignment": "[Excellent/Good/Fair/Poor]",
    "feedback": "[2-3 sentence summary of why this score was given]",
    "key_strengths": "[What makes this a good match]",
    "potential_concerns": "[Any concerns or gaps identified]",
    "recommendation": "[Strong Recommend/Recommend/Consider/Not Recommended]"
}}

**SCORING GUIDELINES:**
- 90-100: Exceptional match, highly recommended
- 80-89: Strong match, recommended  
- 70-79: Good match, worth considering
- 60-69: Moderate match, some concerns
- 50-59: Weak match, significant gaps
- 1-49: Poor match, not recommended

Be objective and thorough in your evaluation. Consider both obvious matches and potential for growth.
"""
        
        return prompt.strip()
    
    def get_detailed_feedback_prompt(self, job: Dict, profile_data: Dict, score: int) -> str:
        """Get prompt for generating detailed feedback document"""
        
        job_title = job.get('title', 'N/A')
        job_company = job.get('company', 'N/A')
        
        prompt = f"""
Generate a detailed evaluation report for this job opportunity:

**Job:** {job_title} at {job_company}
**Match Score:** {score}/100

Based on the candidate's profile and this job opportunity, provide a comprehensive evaluation report that includes:

1. **Executive Summary** (2-3 sentences)
2. **Detailed Skills Analysis** 
   - Skills that align well
   - Skills gaps identified
   - Transferable skills
3. **Experience Assessment**
   - Relevant experience highlights
   - Experience gaps or concerns
4. **Strategic Considerations**
   - Career progression potential
   - Industry fit
   - Long-term career alignment
5. **Recommendation**
   - Should the candidate apply? Why or why not?
   - Any suggestions for strengthening the application

Keep the tone professional but encouraging. Focus on actionable insights.
Format as a structured document with clear headings.
"""
        
        return prompt.strip()
    
    def get_comparison_prompt(self, jobs: List[Dict]) -> str:
        """Get prompt for comparing multiple job opportunities"""
        
        job_list = ""
        for i, job in enumerate(jobs[:5], 1):  # Limit to top 5 jobs
            job_list += f"{i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')} (Score: {job.get('match_score', 0)})\n"
        
        prompt = f"""
You are a career advisor helping a candidate choose between multiple job opportunities. 

**TOP JOB OPPORTUNITIES:**
{job_list}

Please provide:

1. **Comparative Analysis:** Brief comparison of the top opportunities
2. **Prioritization:** Which jobs should be prioritized and why?
3. **Application Strategy:** Recommendations for approaching these opportunities
4. **Timeline Considerations:** Any timing factors to consider

Keep the analysis concise but actionable. Focus on strategic career decisions.
"""
        
        return prompt.strip()
    
    def get_resume_customization_prompt(self, job: Dict, profile_data: Dict) -> str:
        """Get prompt for resume customization"""
        
        job_title = job.get('title', 'N/A')
        job_company = job.get('company', 'N/A')
        job_description = job.get('description', '')
        
        linkedin_profile = profile_data.get('linkedin_pdf', '')
        summary = profile_data.get('summary_txt', '')
        
        prompt = f"""
You are a professional resume writer. Customize the candidate's resume for this specific job opportunity.

**TARGET JOB:**
Title: {job_title}
Company: {job_company}
Description: {job_description[:800] if job_description else 'Limited description'}

**CANDIDATE PROFILE:**
{linkedin_profile[:1000] if linkedin_profile else 'Profile not available'}

**PROFESSIONAL SUMMARY:**
{summary[:500] if summary else 'Summary not available'}

**CUSTOMIZATION REQUIREMENTS:**

1. **Professional Summary:** Write a compelling 3-4 line summary tailored to this role
2. **Key Skills:** List 8-10 most relevant skills for this position  
3. **Experience Highlights:** Identify 3-4 key achievements to emphasize
4. **Keywords:** Extract important keywords from job description to include
5. **ATS Optimization:** Ensure resume will pass Applicant Tracking Systems

**RESPONSE FORMAT:**
Provide structured recommendations for:
- Opening summary paragraph
- Skills section content
- Experience section emphasis
- Keywords to incorporate
- Overall positioning strategy

Make it specific to this job while maintaining truthfulness about the candidate's background.
"""
        
        return prompt.strip()
    
    def get_cover_letter_prompt(self, job: Dict, profile_data: Dict) -> str:
        """Get prompt for cover letter generation"""
        
        job_title = job.get('title', 'N/A')
        job_company = job.get('company', 'N/A')
        job_description = job.get('description', '')
        
        prompt = f"""
Write a compelling cover letter for this job application:

**POSITION:** {job_title} at {job_company}
**JOB DESCRIPTION:** {job_description[:600] if job_description else 'Limited description'}

**CANDIDATE BACKGROUND:** [Use profile data provided in previous context]

**COVER LETTER REQUIREMENTS:**
- Professional tone, confident but not arrogant
- 3-4 paragraphs maximum
- Address specific job requirements
- Highlight relevant achievements
- Show genuine interest in the company/role
- Include a strong call to action

**STRUCTURE:**
1. Opening: Hook and position interest
2. Body: Match skills/experience to job requirements
3. Closing: Express enthusiasm and next steps

Make it personal and specific to this opportunity while maintaining professionalism.
"""
        
        return prompt.strip()
    
    def get_interview_prep_prompt(self, job: Dict, profile_data: Dict) -> str:
        """Get prompt for interview preparation"""
        
        job_title = job.get('title', 'N/A')
        job_company = job.get('company', 'N/A')
        job_description = job.get('description', '')
        
        prompt = f"""
Prepare interview guidance for this job opportunity:

**POSITION:** {job_title} at {job_company}
**ROLE DETAILS:** {job_description[:600] if job_description else 'Limited description'}

Based on the candidate's background, provide:

1. **Likely Interview Questions** (5-7 questions specific to this role)
2. **Suggested Answers Framework** (Key points to cover for each question)
3. **Questions to Ask the Interviewer** (3-4 thoughtful questions)
4. **Key Stories to Prepare** (2-3 STAR method examples)
5. **Company Research Topics** (What to research about the company)
6. **Potential Concerns to Address** (Weaknesses or gaps to proactively address)

Focus on helping the candidate present their best case for this specific role.
"""
        
        return prompt.strip()