"""Setup script for Trade Alerts"""

import os

def create_env_file():
    """Create .env file from template"""
    env_file = '.env'
    env_example = '.env.example'
    
    if os.path.exists(env_file):
        print(f"✅ {env_file} already exists")
        return
    
    if os.path.exists(env_example):
        with open(env_example, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Created {env_file} from {env_example}")
        print("⚠️  Please edit .env and fill in your configuration values")
    else:
        print(f"⚠️  {env_example} not found - creating basic .env file")
        
        basic_env = """# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=
GOOGLE_DRIVE_CREDENTIALS_JSON=
GOOGLE_DRIVE_REFRESH_TOKEN=

# Pushover Configuration
PUSHOVER_API_TOKEN=
PUSHOVER_USER_KEY=

# Price API Configuration
PRICE_API_URL=https://api.exchangerate-api.com/v4/latest/USD

# Monitoring Configuration
CHECK_INTERVAL=60
ENTRY_TOLERANCE_PIPS=10
ENTRY_TOLERANCE_PERCENT=0.1
ANALYSIS_REFRESH_INTERVAL=15
"""
        
        with open(env_file, 'w') as f:
            f.write(basic_env)
        
        print(f"✅ Created basic {env_file}")
        print("⚠️  Please edit .env and fill in your configuration values")

def create_directories():
    """Create necessary directories"""
    dirs = ['data', 'logs']
    
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✅ Created directory: {dir_name}")
        else:
            print(f"✅ Directory exists: {dir_name}")

def main():
    """Run setup"""
    print("=" * 60)
    print("Trade Alerts Setup")
    print("=" * 60)
    print()
    
    create_directories()
    print()
    create_env_file()
    print()
    
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Edit .env file and add your configuration:")
    print("   - GOOGLE_DRIVE_FOLDER_ID (your Forex tracker folder ID)")
    print("   - GOOGLE_DRIVE_CREDENTIALS_JSON (from Google Cloud Console)")
    print("   - GOOGLE_DRIVE_REFRESH_TOKEN (OAuth2 refresh token)")
    print("   - PUSHOVER_API_TOKEN (from pushover.net)")
    print("   - PUSHOVER_USER_KEY (from pushover.net)")
    print()
    print("2. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    print("3. Run the monitor:")
    print("   python main.py")
    print()

if __name__ == '__main__':
    main()

