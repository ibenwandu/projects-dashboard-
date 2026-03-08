import logging
import os
from typing import List, Dict, Optional
from datetime import datetime
from src.storage import SheetsManager, FileManager, GoogleDriveClient
from src.ai import JobEvaluator
from src.utils import NameFormatter, DocxGenerator
from src.config import Config

class ResumeGenerationAgent:
    """Agent 2: Resume generation for selected jobs"""
    
    def __init__(self):
        self.config = Config()
        self.sheets_manager = SheetsManager()
        self.file_manager = FileManager()
        self.drive_client = GoogleDriveClient()
        self.job_evaluator = JobEvaluator()
        self.name_formatter = NameFormatter()
        self.docx_generator = DocxGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Setup logging
        if not self.logger.handlers:
            logging.basicConfig(
                level=getattr(logging, self.config.LOG_LEVEL.upper()),
                format=self.config.LOG_FORMAT,
                handlers=[
                    logging.FileHandler('logs/resume_agent.log'),
                    logging.StreamHandler()
                ]
            )
    
    def run(self) -> Dict:
        """Main execution method for resume generation agent"""
        self.logger.info("Starting Resume Generation Agent execution")
        
        results = {
            'execution_time': datetime.now(),
            'jobs_checked': 0,
            'jobs_marked_for_application': 0,
            'resumes_generated': 0,
            'feedback_generated': 0,
            'files_uploaded': 0,
            'processed_jobs': [],
            'errors': [],
            'success': False
        }
        
        try:
            # Step 1: Check for jobs marked for application
            self.logger.info("Checking for jobs marked for application")
            marked_jobs = self.sheets_manager.get_jobs_marked_for_application()
            results['jobs_marked_for_application'] = len(marked_jobs)
            
            if not marked_jobs:
                self.logger.info("No jobs marked for application found")
                results['success'] = True
                return results
            
            # Step 2: Get profile data for resume customization
            profile_data = self.file_manager.get_profile_files()
            if not profile_data['success']:
                self.logger.warning("Failed to load profile data")
                results['errors'].extend(profile_data['errors'])
                # Use empty profile as fallback
                profile_data = {'linkedin_pdf': '', 'summary_txt': ''}
            
            # Step 3: Process each marked job
            for job in marked_jobs:
                try:
                    job_result = self._process_single_job(job, profile_data)
                    results['processed_jobs'].append(job_result)
                    
                    # Update counters
                    if job_result.get('resume_generated'):
                        results['resumes_generated'] += 1
                    if job_result.get('feedback_generated'):
                        results['feedback_generated'] += 1
                    if job_result.get('files_uploaded'):
                        results['files_uploaded'] += job_result['files_uploaded']
                    
                    # Update job status in sheets
                    self._update_job_status(job, job_result)
                    
                except Exception as e:
                    error_msg = f"Error processing job {job.get('title', 'unknown')}: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            results['jobs_checked'] = len(marked_jobs)
            results['success'] = len(results['errors']) == 0 or results['resumes_generated'] > 0
            
            # Summary logging
            self.logger.info(f"Resume Generation Agent completed:")
            self.logger.info(f"  - Checked {results['jobs_checked']} marked jobs")
            self.logger.info(f"  - Generated {results['resumes_generated']} resumes")
            self.logger.info(f"  - Generated {results['feedback_generated']} feedback documents")
            self.logger.info(f"  - Uploaded {results['files_uploaded']} files")
            
        except Exception as e:
            error_msg = f"Resume Generation Agent execution failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            results['success'] = False
        
        return results
    
    def _process_single_job(self, job: Dict, profile_data: Dict) -> Dict:
        """Process a single job for resume generation"""
        job_result = {
            'job_title': job.get('title', 'Unknown'),
            'company': job.get('company', 'Unknown'),
            'resume_generated': False,
            'feedback_generated': False,
            'files_uploaded': 0,
            'resume_file_id': None,
            'feedback_file_id': None,
            'errors': []
        }
        
        try:
            self.logger.info(f"Processing job: {job_result['job_title']} at {job_result['company']}")
            
            # Skip if resume already generated
            if job.get('resume_status') == 'Completed':
                self.logger.info("Resume already generated for this job, skipping")
                return job_result
            
            # Step 1: Generate customized resume
            resume_result = self._generate_customized_resume(job, profile_data)
            if resume_result['success']:
                job_result['resume_generated'] = True
                job_result['resume_file_id'] = resume_result['file_id']
                job_result['files_uploaded'] += 1
                self.logger.info(f"Generated resume: {resume_result['filename']}")
            else:
                job_result['errors'].extend(resume_result['errors'])
            
            # Step 2: Generate evaluation feedback document
            feedback_result = self._generate_feedback_document(job, profile_data)
            if feedback_result['success']:
                job_result['feedback_generated'] = True
                job_result['feedback_file_id'] = feedback_result['file_id']
                job_result['files_uploaded'] += 1
                self.logger.info(f"Generated feedback: {feedback_result['filename']}")
            else:
                job_result['errors'].extend(feedback_result['errors'])
            
        except Exception as e:
            error_msg = f"Error in _process_single_job: {str(e)}"
            job_result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return job_result
    
    def _generate_customized_resume(self, job: Dict, profile_data: Dict) -> Dict:
        """Generate customized resume for specific job"""
        result = {
            'success': False,
            'filename': '',
            'file_id': None,
            'errors': []
        }
        
        try:
            # Generate resume customization using AI
            customization_prompt = self.job_evaluator.prompts.get_resume_customization_prompt(job, profile_data)
            
            # Get AI recommendations for customization
            if self.config.CLAUDE_API_KEY:
                response = self.job_evaluator.claude_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=800,
                    messages=[{
                        "role": "user",
                        "content": customization_prompt
                    }]
                )
                customization_text = response.content[0].text
            elif self.config.OPENAI_API_KEY:
                import openai
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{
                        "role": "user",
                        "content": customization_prompt
                    }],
                    max_tokens=800,
                    temperature=0.3
                )
                customization_text = response.choices[0].message.content
            else:
                customization_text = "Basic resume customization - AI not available"
            
            # Parse customization recommendations
            customization_data = self._parse_customization_response(customization_text)
            
            # Generate DOCX resume
            resume_doc = self.docx_generator.create_resume_document(
                profile_data, job, customization_data)
            
            # Generate filename
            filename = self.name_formatter.format_resume_filename(
                job.get('company', 'Unknown'),
                job.get('title', 'Unknown'),
                'Resume'
            )
            
            # Upload to Google Drive Results folder
            results_folder_id = self.drive_client.get_or_create_results_folder()
            if results_folder_id:
                file_id = self.drive_client.upload_file(
                    file_content=resume_doc.getvalue(),
                    file_name=filename,
                    folder_id=results_folder_id,
                    mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                
                if file_id:
                    result['success'] = True
                    result['filename'] = filename
                    result['file_id'] = file_id
                else:
                    result['errors'].append("Failed to upload resume to Google Drive")
            else:
                result['errors'].append("Failed to access Results folder in Google Drive")
            
        except Exception as e:
            error_msg = f"Error generating customized resume: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _generate_feedback_document(self, job: Dict, profile_data: Dict) -> Dict:
        """Generate evaluation feedback document"""
        result = {
            'success': False,
            'filename': '',
            'file_id': None,
            'errors': []
        }
        
        try:
            # Create evaluation data structure
            evaluation_data = {
                'match_score': job.get('score', 0),
                'feedback': job.get('reasoning', 'No detailed feedback available'),
                'recommendation': 'Apply' if int(str(job.get('score', 0))) >= 85 else 'Consider',
                'skills_match': 'Good',
                'experience_match': 'Good',
                'key_strengths': 'Profile alignment with job requirements',
                'potential_concerns': 'Review job description for specific requirements'
            }
            
            # Generate detailed feedback if AI is available
            if (self.config.CLAUDE_API_KEY or self.config.OPENAI_API_KEY) and job.get('score'):
                try:
                    detailed_feedback = self.job_evaluator.generate_detailed_feedback(
                        job, profile_data, int(str(job.get('score', 0)))
                    )
                    evaluation_data['feedback'] = detailed_feedback
                except Exception as e:
                    self.logger.warning(f"Failed to generate detailed feedback: {str(e)}")
            
            # Generate DOCX feedback document
            feedback_doc = self.docx_generator.create_feedback_document(job, evaluation_data)
            
            # Generate filename
            filename = self.name_formatter.format_feedback_filename(
                job.get('company', 'Unknown'),
                job.get('title', 'Unknown')
            )
            
            # Upload to Google Drive Results folder
            results_folder_id = self.drive_client.get_or_create_results_folder()
            if results_folder_id:
                file_id = self.drive_client.upload_file(
                    file_content=feedback_doc.getvalue(),
                    file_name=filename,
                    folder_id=results_folder_id,
                    mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                
                if file_id:
                    result['success'] = True
                    result['filename'] = filename
                    result['file_id'] = file_id
                else:
                    result['errors'].append("Failed to upload feedback to Google Drive")
            else:
                result['errors'].append("Failed to access Results folder in Google Drive")
            
        except Exception as e:
            error_msg = f"Error generating feedback document: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _parse_customization_response(self, response_text: str) -> Dict:
        """Parse AI customization response into structured data"""
        try:
            # Simple parsing - look for key sections
            customization = {
                'professional_summary': '',
                'key_skills': [],
                'experience_highlights': [],
                'keywords': []
            }
            
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if 'professional summary' in line.lower():
                    current_section = 'professional_summary'
                elif 'key skills' in line.lower() or 'skills' in line.lower():
                    current_section = 'key_skills'
                elif 'experience' in line.lower():
                    current_section = 'experience_highlights'
                elif 'keyword' in line.lower():
                    current_section = 'keywords'
                elif line.startswith('-') or line.startswith('•'):
                    # Bullet point
                    item = line[1:].strip()
                    if current_section == 'key_skills':
                        customization['key_skills'].append(item)
                    elif current_section == 'experience_highlights':
                        customization['experience_highlights'].append(item)
                    elif current_section == 'keywords':
                        customization['keywords'].append(item)
                else:
                    # Regular text
                    if current_section == 'professional_summary':
                        if customization['professional_summary']:
                            customization['professional_summary'] += ' '
                        customization['professional_summary'] += line
            
            # Fallback values
            if not customization['professional_summary']:
                customization['professional_summary'] = "Experienced professional seeking new opportunities in a dynamic environment."
            
            if not customization['key_skills']:
                customization['key_skills'] = ["Communication", "Problem Solving", "Team Collaboration", "Project Management"]
            
            return customization
            
        except Exception as e:
            self.logger.error(f"Error parsing customization response: {str(e)}")
            return {
                'professional_summary': "Experienced professional with strong background in relevant field.",
                'key_skills': ["Communication", "Problem Solving", "Team Collaboration"],
                'experience_highlights': ["Strong track record of success"],
                'keywords': []
            }
    
    def _update_job_status(self, job: Dict, job_result: Dict) -> bool:
        """Update job status in Google Sheets"""
        try:
            job_url = job.get('url', '')
            if not job_url:
                return False
            
            # Determine status
            if job_result['resume_generated'] and job_result['feedback_generated']:
                status = 'Completed'
            elif job_result['resume_generated']:
                status = 'Resume Generated'
            elif job_result['errors']:
                status = 'Failed'
            else:
                status = 'In Progress'
            
            # Generate resume link if available
            resume_link = ''
            if job_result['resume_file_id']:
                resume_link = f"https://drive.google.com/file/d/{job_result['resume_file_id']}/view"
            
            # Update sheets
            success = self.sheets_manager.update_resume_status(
                job_url=job_url,
                status=status,
                resume_link=resume_link,
                generated_date=datetime.now().strftime('%Y-%m-%d %H:%M')
            )
            
            if success:
                self.logger.info(f"Updated status for {job.get('title', 'unknown')} to {status}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating job status: {str(e)}")
            return False
    
    def monitor_apply_column(self) -> Dict:
        """Monitor for newly marked jobs (can be called periodically)"""
        try:
            marked_jobs = self.sheets_manager.get_jobs_marked_for_application()
            
            # Filter for jobs that need resume generation
            pending_jobs = [
                job for job in marked_jobs 
                if not job.get('resume_status') or job.get('resume_status') in ['', 'In Progress', 'Failed']
            ]
            
            return {
                'total_marked': len(marked_jobs),
                'pending_resume_generation': len(pending_jobs),
                'jobs': pending_jobs
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring apply column: {str(e)}")
            return {'total_marked': 0, 'pending_resume_generation': 0, 'jobs': []}