"""
Prompt templates for AI-powered job evaluation and resume generation.
"""

JOB_EVALUATION_PROMPT = """
You are an AI career advisor analyzing job opportunities for candidate fit. 

CANDIDATE PROFILE:
{profile_summary}

JOB POSTING:
Title: {job_title}
Company: {company}
Location: {location}
Description: {job_description}

EVALUATION CRITERIA:
1. Skills Alignment (30%): How well do the candidate's skills match the required/preferred skills?
2. Experience Relevance (25%): How relevant is the candidate's work experience to this role?
3. Education Match (15%): Does the candidate's education align with requirements?
4. Industry Experience (15%): Experience in the same or related industry?
5. Role Responsibilities Fit (15%): How well do past responsibilities prepare for this role?

INSTRUCTIONS:
- Score from 1-100 (1 = poor fit, 100 = perfect fit)
- Be realistic and objective
- Consider both required and preferred qualifications
- Focus on transferable skills and relevant experience

Provide your response in this exact format:
SCORE: [numerical score]
REASONING: [2-3 sentences explaining the score, highlighting key matches and gaps]
"""

RESUME_CUSTOMIZATION_PROMPT = """
You are an expert resume writer creating a tailored resume for a specific job application.

ORIGINAL PROFILE:
{profile_summary}

TARGET JOB:
Title: {job_title}
Company: {company}
Description: {job_description}

RESUME CUSTOMIZATION REQUIREMENTS:
1. Tailor the professional summary to highlight most relevant experience
2. Reorder and emphasize skills that match job requirements
3. Adjust experience descriptions to emphasize relevant achievements
4. Include industry-specific keywords naturally
5. Ensure ATS optimization while maintaining readability
6. Keep all information factually accurate - DO NOT fabricate experience

INSTRUCTIONS:
- Maintain the candidate's actual experience and education
- Emphasize transferable skills and relevant accomplishments
- Use action verbs and quantifiable achievements where possible
- Include keywords from the job posting naturally
- Format for ATS scanning (clear headings, standard formatting)

Provide a complete resume in this format:

PROFESSIONAL SUMMARY:
[Tailored 3-4 line summary]

CORE COMPETENCIES:
[Bullet points of relevant skills]

PROFESSIONAL EXPERIENCE:
[Detailed experience with emphasis on relevant aspects]

EDUCATION:
[Education details]

ADDITIONAL SECTIONS:
[Any relevant certifications, achievements, etc.]
"""

KEYWORD_OPTIMIZATION_PROMPT = """
Analyze the following job description and extract the most important keywords and phrases that should be included in a resume for ATS optimization.

JOB DESCRIPTION:
{job_description}

Extract and categorize keywords into:
1. MUST-HAVE SKILLS: Core technical/professional skills required
2. PREFERRED SKILLS: Nice-to-have skills mentioned
3. INDUSTRY TERMS: Specific industry jargon and terminology
4. SOFT SKILLS: Leadership, communication, teamwork terms
5. TOOLS/TECHNOLOGIES: Specific software, platforms, methodologies
6. QUALIFICATIONS: Education, certifications, experience levels

Format your response as:
MUST-HAVE SKILLS: [comma-separated list]
PREFERRED SKILLS: [comma-separated list]
INDUSTRY TERMS: [comma-separated list]
SOFT SKILLS: [comma-separated list]
TOOLS/TECHNOLOGIES: [comma-separated list]
QUALIFICATIONS: [comma-separated list]
"""