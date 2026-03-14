"""Test configuration and LLM setup"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("Configuration Check")
print("=" * 60)
print()

# Check LLM API Keys
print("LLM API Keys:")
print(f"  OPENAI_API_KEY (ChatGPT): {'✅ SET' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET'}")
print(f"  GOOGLE_API_KEY (Gemini): {'✅ SET' if os.getenv('GOOGLE_API_KEY') else '❌ NOT SET'}")
print(f"  ANTHROPIC_API_KEY (Claude): {'✅ SET' if os.getenv('ANTHROPIC_API_KEY') else '❌ NOT SET'}")
print()

# Check Google Drive
print("Google Drive:")
print(f"  GOOGLE_DRIVE_FOLDER_ID: {'✅ SET' if os.getenv('GOOGLE_DRIVE_FOLDER_ID') else '❌ NOT SET'}")
print(f"  GOOGLE_DRIVE_CREDENTIALS_JSON: {'✅ SET' if os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON') else '❌ NOT SET'}")
print(f"  GOOGLE_DRIVE_REFRESH_TOKEN: {'✅ SET' if os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN') else '❌ NOT SET'}")
print()

# Check Email
print("Email:")
print(f"  SENDER_EMAIL: {'✅ SET' if os.getenv('SENDER_EMAIL') else '❌ NOT SET'}")
print(f"  SENDER_PASSWORD: {'✅ SET' if os.getenv('SENDER_PASSWORD') else '❌ NOT SET'}")
print(f"  RECIPIENT_EMAIL: {'✅ SET' if os.getenv('RECIPIENT_EMAIL') else '❌ NOT SET'}")
print()

# Check Pushover
print("Pushover:")
print(f"  PUSHOVER_API_TOKEN: {'✅ SET' if os.getenv('PUSHOVER_API_TOKEN') else '❌ NOT SET'}")
print(f"  PUSHOVER_USER_KEY: {'✅ SET' if os.getenv('PUSHOVER_USER_KEY') else '❌ NOT SET'}")
print()

# Test LLM initialization
print("=" * 60)
print("Testing LLM Initialization")
print("=" * 60)
print()

try:
    from src.llm_analyzer import LLMAnalyzer
    la = LLMAnalyzer()
    print(f"ChatGPT: {'✅ Enabled' if la.chatgpt_enabled else '❌ Disabled'}")
    print(f"Gemini: {'✅ Enabled' if la.gemini_enabled else '❌ Disabled'}")
    print(f"Claude: {'✅ Enabled' if la.claude_enabled else '❌ Disabled'}")
except Exception as e:
    print(f"❌ Error initializing LLMs: {e}")

print()
print("=" * 60)
print("Next Steps:")
print("=" * 60)
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Fill in any missing configuration above")
print("3. Run: python main.py")
print()







