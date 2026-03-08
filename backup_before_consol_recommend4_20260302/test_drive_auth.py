"""Quick test script to verify Google Drive authentication"""

import os
from dotenv import load_dotenv
from src.drive_reader import DriveReader
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

def test_drive_auth():
    """Test Google Drive authentication"""
    logger.info("="*80)
    logger.info("TESTING GOOGLE DRIVE AUTHENTICATION")
    logger.info("="*80)
    logger.info("")
    
    # Check environment variables
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    refresh_token = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
    credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')
    
    logger.info("Environment Variables Check:")
    logger.info(f"  GOOGLE_DRIVE_FOLDER_ID: {'✅ Set' if folder_id else '❌ Not set'}")
    logger.info(f"  GOOGLE_DRIVE_REFRESH_TOKEN: {'✅ Set' if refresh_token else '❌ Not set'}")
    if refresh_token:
        logger.info(f"    Token length: {len(refresh_token)}")
        logger.info(f"    Token preview: {refresh_token[:30]}...")
    logger.info(f"  GOOGLE_DRIVE_CREDENTIALS_JSON: {'✅ Set' if credentials_json else '❌ Not set'}")
    if credentials_json:
        logger.info(f"    JSON length: {len(credentials_json)}")
    logger.info("")
    
    if not folder_id:
        logger.error("❌ GOOGLE_DRIVE_FOLDER_ID not set. Cannot proceed.")
        return False
    
    if not refresh_token:
        logger.error("❌ GOOGLE_DRIVE_REFRESH_TOKEN not set. Cannot proceed.")
        return False
    
    if not credentials_json:
        logger.error("❌ GOOGLE_DRIVE_CREDENTIALS_JSON not set. Cannot proceed.")
        return False
    
    # Try to initialize DriveReader
    logger.info("Attempting to initialize DriveReader...")
    logger.info("-" * 80)
    
    try:
        drive_reader = DriveReader(folder_id)
        
        if drive_reader.enabled:
            logger.info("✅ DriveReader initialized successfully!")
            logger.info("")
            
            # Try to list files
            logger.info("Testing file listing...")
            files = drive_reader.list_files()
            logger.info(f"✅ Successfully listed {len(files)} files")
            
            if len(files) > 0:
                logger.info("Sample files:")
                for f in files[:5]:
                    logger.info(f"  - {f['title']}")
            
            return True
        else:
            logger.error("❌ DriveReader failed to initialize")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = test_drive_auth()
    if success:
        logger.info("")
        logger.info("="*80)
        logger.info("✅ AUTHENTICATION TEST PASSED")
        logger.info("="*80)
    else:
        logger.info("")
        logger.info("="*80)
        logger.info("❌ AUTHENTICATION TEST FAILED")
        logger.info("="*80)
        logger.info("")
        logger.info("Troubleshooting:")
        logger.info("1. Verify GOOGLE_DRIVE_REFRESH_TOKEN is correct and not expired")
        logger.info("2. Verify GOOGLE_DRIVE_CREDENTIALS_JSON is valid JSON")
        logger.info("3. Verify GOOGLE_DRIVE_FOLDER_ID matches your 'Forex tracker' folder")
        logger.info("4. Check that the refresh token has not been revoked in Google Cloud Console")





