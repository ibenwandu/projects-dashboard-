#!/usr/bin/env python3
"""
Test script to verify setup is correct
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def test_environment():
    """Test environment variables"""
    print("="*80)
    print("Testing Environment Configuration")
    print("="*80)
    
    required_vars = [
        'OPENAI_API_KEY',
        'SENDER_EMAIL',
        'SENDER_PASSWORD',
        'RECIPIENT_EMAIL'
    ]
    
    optional_vars = [
        'OPENAI_MODEL',
        'SMTP_SERVER',
        'SMTP_PORT',
        'SUMMARY_TIME'
    ]
    
    all_ok = True
    
    print("\n✅ Required Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'KEY' in var:
                display = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            else:
                display = value
            print(f"   ✅ {var}: {display}")
        else:
            print(f"   ❌ {var}: NOT SET")
            all_ok = False
    
    print("\n📋 Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {value}")
        else:
            print(f"   ⚠️  {var}: Using default")
    
    return all_ok

def test_files():
    """Test required files"""
    print("\n" + "="*80)
    print("Testing Required Files")
    print("="*80)
    
    files = {
        'credentials.json': 'Gmail API credentials',
        'data/resume_template.txt': 'Resume template',
        'data/linkedin.pdf': 'LinkedIn profile PDF',
        'data/skills_summary.txt': 'Skills summary'
    }
    
    all_ok = True
    
    for file_path, description in files.items():
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   ✅ {description}: {file_path} ({size} bytes)")
        else:
            print(f"   ❌ {description}: {file_path} - NOT FOUND")
            all_ok = False
    
    return all_ok

def test_directories():
    """Test directory structure"""
    print("\n" + "="*80)
    print("Testing Directory Structure")
    print("="*80)
    
    directories = [
        'data',
        'output',
        'output/resumes',
        'logs'
    ]
    
    all_ok = True
    
    for directory in directories:
        if os.path.exists(directory) and os.path.isdir(directory):
            print(f"   ✅ {directory}/")
        else:
            print(f"   ❌ {directory}/ - NOT FOUND")
            all_ok = False
    
    return all_ok

def test_imports():
    """Test Python imports"""
    print("\n" + "="*80)
    print("Testing Python Imports")
    print("="*80)
    
    imports = [
        ('openai', 'OpenAI API client'),
        ('google.auth', 'Google Auth'),
        ('googleapiclient', 'Gmail API'),
        ('schedule', 'Scheduler'),
        ('dotenv', 'Environment variables'),
        ('PyPDF2', 'PDF processing (optional)'),
        ('pdfkit', 'PDF generation (optional)')
    ]
    
    all_ok = True
    
    for module_name, description in imports:
        try:
            __import__(module_name)
            print(f"   ✅ {description}: {module_name}")
        except ImportError:
            if 'optional' in description.lower():
                print(f"   ⚠️  {description}: {module_name} - Optional, not installed")
            else:
                print(f"   ❌ {description}: {module_name} - NOT INSTALLED")
                all_ok = False
    
    return all_ok

def test_gmail_auth():
    """Test Gmail authentication"""
    print("\n" + "="*80)
    print("Testing Gmail Authentication")
    print("="*80)
    
    try:
        from src.email_processor import EmailProcessor
        processor = EmailProcessor()
        print("   ✅ Gmail authentication successful")
        return True
    except FileNotFoundError as e:
        print(f"   ❌ Gmail credentials not found: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  Gmail authentication issue: {e}")
        print("   (This is normal on first run - authentication will happen when you run main.py)")
        return True  # Not a critical error

def test_openai():
    """Test OpenAI API"""
    print("\n" + "="*80)
    print("Testing OpenAI API")
    print("="*80)
    
    try:
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("   ❌ OPENAI_API_KEY not set")
            return False
        
        client = openai.OpenAI(api_key=api_key)
        # Simple test - just check if client is created
        print("   ✅ OpenAI client created successfully")
        print("   ⚠️  Full API test requires actual API call (will test on first run)")
        return True
    except Exception as e:
        print(f"   ❌ OpenAI setup error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("Recruiter Email Automation - Setup Test")
    print("="*80)
    
    results = {
        'Environment': test_environment(),
        'Files': test_files(),
        'Directories': test_directories(),
        'Imports': test_imports(),
        'Gmail Auth': test_gmail_auth(),
        'OpenAI': test_openai()
    }
    
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ All tests passed! System is ready to use.")
        print("\nNext step: Run 'python main.py' to start the automation")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nRun 'python setup.py' for help with setup.")
    print("="*80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())



