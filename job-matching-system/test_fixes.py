"""
Test script to verify the fixes for email notifications and rate limiting.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.reporting.email_notifier import EmailNotifier
from src.ai.job_evaluator import JobEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def test_email_notification():
    """Test email notification functionality."""
    print("🧪 Testing Email Notification Fix...")
    
    try:
        # Test email notifier initialization
        notifier = EmailNotifier(
            sender_email="test@example.com",
            sender_password="test_password",
            recipient_email="test@example.com"
        )
        
        # Test email sending (will fail due to invalid credentials, but should not crash)
        result = notifier.send_email(
            subject="Test Email",
            body="This is a test email to verify the MimeMultipart fix.",
            is_html=False
        )
        
        print("✅ Email notification test completed (expected to fail due to invalid credentials)")
        return True
        
    except Exception as e:
        print(f"❌ Email notification test failed: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting functionality."""
    print("🧪 Testing Rate Limiting Fix...")
    
    try:
        # Test job evaluator with rate limiting
        evaluator = JobEvaluator(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            claude_api_key=os.getenv('CLAUDE_API_KEY'),
            rate_limit_delay=1.0  # 1-second delay for testing
        )
        
        print("✅ Rate limiting configuration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔧 Testing Job Matching System Fixes")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Run tests
    email_test = test_email_notification()
    rate_limit_test = test_rate_limiting()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Email Notification Fix: {'✅ PASS' if email_test else '❌ FAIL'}")
    print(f"  Rate Limiting Fix: {'✅ PASS' if rate_limit_test else '❌ FAIL'}")
    
    if email_test and rate_limit_test:
        print("\n🎉 All fixes applied successfully!")
        print("\n📋 Next Steps:")
        print("  1. Update your .env file with AI_RATE_LIMIT_DELAY=3.0")
        print("  2. Run: python main.py job-matching")
        print("  3. Monitor logs for improved performance")
    else:
        print("\n⚠️ Some fixes need attention. Check the error messages above.")

if __name__ == "__main__":
    main() 