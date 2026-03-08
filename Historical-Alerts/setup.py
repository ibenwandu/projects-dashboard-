"""Setup script for Historical Forex News-Price Correlation Prediction System"""

import os
from pathlib import Path

def setup_project():
    """Create necessary directories and .env file"""
    
    project_root = Path(__file__).parent
    
    # Create directories
    directories = ['data', 'logs', 'output']
    for dir_name in directories:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✓ Created directory: {dir_name}/")
    
    # Create .env file if it doesn't exist
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if not env_file.exists():
        if env_example.exists():
            # Copy from example
            env_content = env_example.read_text()
            env_file.write_text(env_content)
            print(f"\n✓ Created .env file from .env.example")
            print("  Please edit .env and add your GOOGLE_API_KEY")
        else:
            # Create basic .env
            env_content = """# Google Gemini API Key
# Get your API key from: https://aistudio.google.com/
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Gemini Model
GEMINI_MODEL=gemini-1.5-flash
"""
            env_file.write_text(env_content)
            print(f"\n✓ Created .env file")
            print("  Please edit .env and add your GOOGLE_API_KEY")
    else:
        print(f"\n✓ .env file already exists")
    
    print(f"\n{'='*60}")
    print("SETUP COMPLETE")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. Edit .env and add your GOOGLE_API_KEY")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the system: python main.py")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    setup_project()







