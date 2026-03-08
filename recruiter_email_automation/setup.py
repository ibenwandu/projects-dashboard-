#!/usr/bin/env python3
"""
Setup script for Recruiter Email Automation System
Helps users configure the system
"""

import os
import shutil
from pathlib import Path

def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    env_path = Path('.env')
    env_example_path = Path('.env.example')
    
    if env_path.exists():
        print("✅ .env file already exists")
        return
    
    if env_example_path.exists():
        shutil.copy(env_example_path, env_path)
        print("✅ Created .env file from .env.example")
        print("⚠️  Please edit .env and fill in your configuration values")
    else:
        print("❌ .env.example not found")
        # Create basic .env file
        with open(env_path, 'w') as f:
            f.write("""# OpenAI Configuration
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Email Configuration
SENDER_EMAIL=
SENDER_PASSWORD=
RECIPIENT_EMAIL=

# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Summary Time
SUMMARY_TIME=19:00

# File Paths
RESUME_TEMPLATE_PATH=data/resume_template.txt
LINKEDIN_PDF_PATH=data/linkedin.pdf
SKILLS_SUMMARY_PATH=data/skills_summary.txt
""")
        print("✅ Created .env file")
        print("⚠️  Please edit .env and fill in your configuration values")

def check_data_files():
    """Check if required data files exist"""
    print("\n📁 Checking data files...")
    
    files_to_check = {
        'data/resume_template.txt': 'Resume template',
        'data/linkedin.pdf': 'LinkedIn PDF',
        'data/skills_summary.txt': 'Skills summary'
    }
    
    missing_files = []
    for file_path, description in files_to_check.items():
        if os.path.exists(file_path):
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ {description}: {file_path} - MISSING")
            missing_files.append((file_path, description))
    
    if missing_files:
        print("\n⚠️  Missing files:")
        for file_path, description in missing_files:
            print(f"   - {description}: {file_path}")
        print("\nPlease create these files before running the automation.")
    
    return len(missing_files) == 0

def check_credentials():
    """Check if Gmail credentials exist"""
    print("\n🔐 Checking Gmail credentials...")
    
    if os.path.exists('credentials.json'):
        print("✅ credentials.json found")
        return True
    else:
        print("❌ credentials.json not found")
        print("\nPlease:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Gmail API")
        print("3. Create OAuth 2.0 credentials")
        print("4. Download as credentials.json")
        return False

def main():
    """Main setup function"""
    print("="*80)
    print("Recruiter Email Automation System - Setup")
    print("="*80)
    
    # Create directories
    print("\n📂 Creating directories...")
    directories = ['data', 'output/resumes', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ {directory}/")
    
    # Create .env file
    print("\n⚙️  Setting up environment...")
    create_env_file()
    
    # Check data files
    data_files_ok = check_data_files()
    
    # Check credentials
    credentials_ok = check_credentials()
    
    # Summary
    print("\n" + "="*80)
    print("Setup Summary")
    print("="*80)
    
    if credentials_ok and data_files_ok:
        print("✅ All required files are present!")
        print("\nNext steps:")
        print("1. Edit .env file with your configuration")
        print("2. Run: python main.py")
    else:
        print("⚠️  Some setup steps are incomplete:")
        if not credentials_ok:
            print("   - Gmail credentials.json is missing")
        if not data_files_ok:
            print("   - Some data files are missing")
        print("\nPlease complete the setup before running the automation.")

if __name__ == "__main__":
    main()



