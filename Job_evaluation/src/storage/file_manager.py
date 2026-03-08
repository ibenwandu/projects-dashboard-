import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from src.storage.google_drive_client import GoogleDriveClient
from src.config import Config

class FileManager:
    """Manages file operations for raw alerts and results storage"""
    
    def __init__(self):
        self.config = Config()
        self.drive_client = GoogleDriveClient()
        self.logger = logging.getLogger(__name__)
        
        # Folder IDs (will be populated on first use)
        self.alerts_folder_id = None
        self.results_folder_id = None
    
    def store_raw_email_alerts(self, emails: List[Dict]) -> Dict:
        """Store raw email alerts in Google Drive Alerts folder"""
        results = {
            'success': False,
            'stored_count': 0,
            'failed_count': 0,
            'file_ids': [],
            'errors': []
        }
        
        try:
            # Get or create alerts folder
            if not self.alerts_folder_id:
                self.alerts_folder_id = self.drive_client.get_or_create_alerts_folder()
            
            if not self.alerts_folder_id:
                results['errors'].append("Failed to access Alerts folder")
                return results
            
            # Store each email
            for email in emails:
                try:
                    file_id = self.drive_client.upload_raw_email(
                        email_data=email,
                        folder_id=self.alerts_folder_id
                    )
                    
                    if file_id:
                        results['file_ids'].append(file_id)
                        results['stored_count'] += 1
                    else:
                        results['failed_count'] += 1
                        results['errors'].append(f"Failed to store email {email.get('id', 'unknown')}")
                        
                except Exception as e:
                    results['failed_count'] += 1
                    error_msg = f"Error storing email {email.get('id', 'unknown')}: {str(e)}"
                    results['errors'].append(error_msg)
                    self.logger.error(error_msg)
            
            results['success'] = results['stored_count'] > 0
            self.logger.info(f"Stored {results['stored_count']} raw email alerts in Google Drive")
            
        except Exception as e:
            error_msg = f"Error in store_raw_email_alerts: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def store_extracted_jobs(self, jobs: List[Dict]) -> Dict:
        """Store extracted job data in Google Drive Alerts folder"""
        results = {
            'success': False,
            'file_id': None,
            'errors': []
        }
        
        try:
            # Get or create alerts folder
            if not self.alerts_folder_id:
                self.alerts_folder_id = self.drive_client.get_or_create_alerts_folder()
            
            if not self.alerts_folder_id:
                results['errors'].append("Failed to access Alerts folder")
                return results
            
            # Store job data
            file_id = self.drive_client.upload_job_data(
                jobs=jobs,
                folder_id=self.alerts_folder_id
            )
            
            if file_id:
                results['file_id'] = file_id
                results['success'] = True
                self.logger.info(f"Stored extracted jobs data in Google Drive: {file_id}")
            else:
                results['errors'].append("Failed to upload job data")
            
        except Exception as e:
            error_msg = f"Error storing extracted jobs: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def store_evaluation_results(self, evaluation_results: List[Dict]) -> Dict:
        """Store AI evaluation results in Google Drive Results folder"""
        results = {
            'success': False,
            'file_id': None,
            'errors': []
        }
        
        try:
            # Get or create results folder
            if not self.results_folder_id:
                self.results_folder_id = self.drive_client.get_or_create_results_folder()
            
            if not self.results_folder_id:
                results['errors'].append("Failed to access Results folder")
                return results
            
            # Prepare evaluation data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"job_evaluations_{timestamp}.json"
            
            evaluation_data = {
                'evaluation_time': datetime.now().isoformat(),
                'total_evaluations': len(evaluation_results),
                'evaluations': evaluation_results
            }
            
            # Upload evaluation results
            file_id = self.drive_client.upload_file(
                file_content=str(evaluation_data),
                file_name=file_name,
                folder_id=self.results_folder_id,
                mime_type='application/json'
            )
            
            if file_id:
                results['file_id'] = file_id
                results['success'] = True
                self.logger.info(f"Stored evaluation results in Google Drive: {file_id}")
            else:
                results['errors'].append("Failed to upload evaluation results")
            
        except Exception as e:
            error_msg = f"Error storing evaluation results: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def store_job_evaluation_report(self, report_data: Dict) -> Dict:
        """Store job evaluation report in Google Drive Reports folder"""
        results = {
            'success': False,
            'file_id': None,
            'errors': []
        }
        
        try:
            # Get or create reports folder
            reports_folder_id = self.drive_client.get_or_create_reports_folder()
            
            if not reports_folder_id:
                results['errors'].append("Failed to access Reports folder")
                return results
            
            # Prepare report data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"job_evaluation_report_{timestamp}.docx"
            
            # Generate DOCX report
            from src.utils.docx_generator import DocxGenerator
            docx_generator = DocxGenerator()
            report_doc = docx_generator.create_summary_report(report_data)
            
            # Upload report
            file_id = self.drive_client.upload_file(
                file_content=report_doc.getvalue(),
                file_name=file_name,
                folder_id=reports_folder_id,
                mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
            if file_id:
                results['file_id'] = file_id
                results['success'] = True
                self.logger.info(f"Stored job evaluation report in Google Drive: {file_id}")
            else:
                results['errors'].append("Failed to upload job evaluation report")
            
        except Exception as e:
            error_msg = f"Error storing job evaluation report: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def get_profile_files(self) -> Dict:
        """Download and cache profile files from Google Drive"""
        profiles = {
            'linkedin_pdf': None,
            'summary_txt': None,
            'success': False,
            'errors': []
        }
        
        try:
            # Download LinkedIn PDF
            if self.config.LINKEDIN_PDF_ID:
                try:
                    linkedin_content = self.drive_client.download_file(self.config.LINKEDIN_PDF_ID)
                    if linkedin_content:
                        profiles['linkedin_pdf'] = linkedin_content
                        self.logger.info("Downloaded LinkedIn profile")
                    else:
                        profiles['errors'].append("Failed to download LinkedIn PDF")
                except Exception as e:
                    profiles['errors'].append(f"Error downloading LinkedIn PDF: {str(e)}")
            
            # Download Summary TXT
            if self.config.SUMMARY_TXT_ID:
                try:
                    summary_content = self.drive_client.download_file(self.config.SUMMARY_TXT_ID)
                    if summary_content:
                        profiles['summary_txt'] = summary_content
                        self.logger.info("Downloaded summary text")
                    else:
                        profiles['errors'].append("Failed to download Summary TXT")
                except Exception as e:
                    profiles['errors'].append(f"Error downloading Summary TXT: {str(e)}")
            
            profiles['success'] = (profiles['linkedin_pdf'] is not None or 
                                 profiles['summary_txt'] is not None)
            
        except Exception as e:
            error_msg = f"Error getting profile files: {str(e)}"
            profiles['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return profiles
    
    def list_stored_alerts(self) -> List[Dict]:
        """List all stored email alerts"""
        try:
            if not self.alerts_folder_id:
                self.alerts_folder_id = self.drive_client.get_or_create_alerts_folder()
            
            if self.alerts_folder_id:
                return self.drive_client.list_files_in_folder(self.alerts_folder_id)
            
        except Exception as e:
            self.logger.error(f"Error listing stored alerts: {str(e)}")
        
        return []
    
    def list_stored_results(self) -> List[Dict]:
        """List all stored results"""
        try:
            if not self.results_folder_id:
                self.results_folder_id = self.drive_client.get_or_create_results_folder()
            
            if self.results_folder_id:
                return self.drive_client.list_files_in_folder(self.results_folder_id)
            
        except Exception as e:
            self.logger.error(f"Error listing stored results: {str(e)}")
        
        return []
    
    def cleanup_old_files(self, days_old: int = 30) -> Dict:
        """Clean up files older than specified days"""
        # TODO: Implement cleanup logic
        # This would remove files older than X days from both folders
        pass