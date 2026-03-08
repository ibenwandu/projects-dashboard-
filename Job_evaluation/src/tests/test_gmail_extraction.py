import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gmail import GmailClient, EmailParser, JobExtractor
from src.agents import GmailJobAgent
from src.config import Config

class TestGmailExtraction(unittest.TestCase):
    """Test Gmail extraction functionality - Milestone 1"""
    
    def setUp(self):
        """Setup test environment"""
        self.config = Config()
        self.gmail_client = GmailClient()
        self.email_parser = EmailParser()
        self.job_extractor = JobExtractor()
        self.gmail_agent = GmailJobAgent()
    
    def test_gmail_connection(self):
        """Test Gmail API connection"""
        print("Testing Gmail API connection...")
        
        # Test authentication
        connection_successful = self.gmail_client.authenticate()
        
        self.assertTrue(connection_successful, "Gmail API connection should be successful")
        self.assertIsNotNone(self.gmail_client.service, "Gmail service should be initialized")
        
        print("✅ Gmail API connection established successfully")
    
    def test_job_alert_retrieval(self):
        """Test retrieving job alerts from last 7 days"""
        print("Testing job alert retrieval...")
        
        # Authenticate first
        auth_success = self.gmail_client.authenticate()
        self.assertTrue(auth_success, "Gmail authentication required for this test")
        
        # Retrieve emails
        emails = self.gmail_client.get_recent_emails(days=7)
        
        # Basic checks
        self.assertIsInstance(emails, list, "Should return a list of emails")
        
        if emails:
            # Check email structure
            sample_email = emails[0]
            required_fields = ['id', 'subject', 'sender', 'date', 'body']
            
            for field in required_fields:
                self.assertIn(field, sample_email, f"Email should contain {field}")
            
            print(f"✅ Retrieved {len(emails)} emails from last 7 days")
        else:
            print("⚠️  No emails found in last 7 days (this may be normal)")
    
    def test_sender_extraction(self):
        """Test extracting sender information"""
        print("Testing sender extraction...")
        
        # Test various sender formats
        test_senders = [
            "LinkedIn <jobs-noreply@linkedin.com>",
            "jobs-noreply@indeed.com",
            "Job Alerts <noreply@glassdoor.com>",
            "Monster Jobs <monster@email.monster.com>"
        ]
        
        for sender_string in test_senders:
            sender_info = self.email_parser._extract_sender_info(sender_string)
            
            self.assertIsInstance(sender_info, dict, "Should return a dictionary")
            self.assertIn('email', sender_info, "Should extract email")
            self.assertIn('name', sender_info, "Should extract name")
            self.assertTrue(sender_info['email'], "Email should not be empty")
            
            print(f"✅ Extracted sender info from: {sender_string}")
            print(f"   Email: {sender_info['email']}, Name: {sender_info['name']}")
    
    def test_job_alert_identification(self):
        """Test identifying job alert emails"""
        print("Testing job alert identification...")
        
        # Test job alert detection
        mock_job_email = {
            'subject': 'New job recommendations for Business Analyst',
            'sender': 'LinkedIn <jobs-noreply@linkedin.com>',
            'body': 'We found some great job opportunities for you...',
            'snippet': 'Job recommendations based on your profile'
        }
        
        mock_non_job_email = {
            'subject': 'Your weekly digest',
            'sender': 'newsletter@example.com',
            'body': 'Here are the latest news updates...',
            'snippet': 'Weekly newsletter content'
        }
        
        # Test positive case
        is_job_alert = self.gmail_client.is_job_alert(mock_job_email)
        self.assertTrue(is_job_alert, "Should identify job alert email")
        
        # Test negative case
        is_not_job_alert = self.gmail_client.is_job_alert(mock_non_job_email)
        self.assertFalse(is_not_job_alert, "Should not identify non-job email as job alert")
        
        print("✅ Job alert identification working correctly")
    
    def test_email_parsing(self):
        """Test email parsing functionality"""
        print("Testing email parsing...")
        
        mock_email = {
            'id': 'test123',
            'subject': 'New Job Alert: Senior Business Analyst',
            'sender': 'LinkedIn Jobs <jobs-noreply@linkedin.com>',
            'date': 'Thu, 25 Jul 2024 10:30:00 -0400',
            'body': '<html><body>Great opportunities await...</body></html>',
            'snippet': 'Job opportunities in your area'
        }
        
        parsed_email = self.email_parser.parse_job_email(mock_email)
        
        # Verify parsing results
        self.assertIsInstance(parsed_email, dict, "Should return parsed email dict")
        self.assertEqual(parsed_email['email_id'], 'test123')
        self.assertEqual(parsed_email['subject'], 'New Job Alert: Senior Business Analyst')
        self.assertEqual(parsed_email['source_type'], 'LinkedIn')
        
        # Check sender parsing
        sender_info = parsed_email['sender']
        self.assertIsInstance(sender_info, dict, "Sender should be parsed into dict")
        self.assertEqual(sender_info['email'], 'jobs-noreply@linkedin.com')
        
        print("✅ Email parsing working correctly")
    
    def test_job_extraction(self):
        """Test job data extraction"""
        print("Testing job data extraction...")
        
        mock_parsed_email = {
            'email_id': 'test123',
            'source_type': 'LinkedIn',
            'body_html': '''
                <html>
                    <body>
                        <div class="job">
                            <a href="https://linkedin.com/jobs/view/123456">Senior Business Analyst</a>
                            <div>Company: Tech Corp</div>
                            <div>Location: Toronto, ON</div>
                        </div>
                    </body>
                </html>
            ''',
            'body_text': 'Senior Business Analyst at Tech Corp in Toronto, ON',
            'sender': {'email': 'jobs@linkedin.com', 'name': 'LinkedIn'},
            'date': '2024-07-25'
        }
        
        jobs = self.job_extractor.extract_job_data(mock_parsed_email)
        
        self.assertIsInstance(jobs, list, "Should return list of jobs")
        
        if jobs:
            job = jobs[0]
            
            # Check required fields
            self.assertIn('title', job, "Job should have title")
            self.assertIn('company', job, "Job should have company")
            self.assertIn('source_type', job, "Job should have source type")
            
            # Validate job data
            is_valid = self.job_extractor.validate_job_data(job)
            self.assertTrue(is_valid, "Extracted job should be valid")
            
            print(f"✅ Extracted job: {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
        else:
            print("⚠️  No jobs extracted (extraction may need refinement)")
    
    def test_end_to_end_gmail_agent(self):
        """Test complete Gmail agent workflow"""
        print("Testing end-to-end Gmail agent workflow...")
        
        # Run the agent
        results = self.gmail_agent.run()
        
        # Verify results structure
        self.assertIsInstance(results, dict, "Should return results dictionary")
        
        required_result_fields = [
            'execution_time', 'emails_processed', 'job_alerts_found',
            'jobs_extracted', 'jobs', 'errors', 'success'
        ]
        
        for field in required_result_fields:
            self.assertIn(field, results, f"Results should contain {field}")
        
        # Check if execution was successful
        if results['success']:
            print(f"✅ Gmail agent executed successfully:")
            print(f"   - Processed {results['emails_processed']} emails")
            print(f"   - Found {results['job_alerts_found']} job alerts")
            print(f"   - Extracted {results['jobs_extracted']} jobs")
            
            if results['errors']:
                print(f"   - {len(results['errors'])} errors occurred")
        else:
            print(f"❌ Gmail agent execution failed:")
            for error in results['errors']:
                print(f"   - {error}")
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        print("Testing configuration validation...")
        
        try:
            Config.validate()
            print("✅ Configuration validation passed")
        except ValueError as e:
            print(f"❌ Configuration validation failed: {str(e)}")
            self.fail("Configuration validation should pass")

if __name__ == '__main__':
    print("Running Milestone 1 Tests: Gmail Integration Foundation")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)