"""
Utility functions for extracting Google Drive file IDs and Sheet IDs from URLs.
"""
import re
import logging

logger = logging.getLogger(__name__)

def extract_file_id_from_url(url: str) -> str:
    """
    Extract Google Drive file ID from various URL formats.
    
    Args:
        url: Google Drive URL (sharing link or direct link)
        
    Returns:
        File ID string, or original string if no ID found
    """
    if not url:
        return url
    
    # If it's already just an ID (no URL format), return as-is
    if not url.startswith('http'):
        return url
    
    # Pattern for Google Drive file URLs
    patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'/d/([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            logger.info(f"Extracted file ID: {file_id} from URL: {url[:50]}...")
            return file_id
    
    logger.warning(f"Could not extract file ID from URL: {url}")
    return url

def extract_sheet_id_from_url(url: str) -> str:
    """
    Extract Google Sheets ID from URL.
    
    Args:
        url: Google Sheets URL
        
    Returns:
        Sheet ID string, or original string if no ID found
    """
    if not url:
        return url
    
    # If it's already just an ID, return as-is
    if not url.startswith('http'):
        return url
    
    # Pattern for Google Sheets URLs
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    
    if match:
        sheet_id = match.group(1)
        logger.info(f"Extracted sheet ID: {sheet_id} from URL: {url[:50]}...")
        return sheet_id
    
    logger.warning(f"Could not extract sheet ID from URL: {url}")
    return url

def extract_folder_id_from_url(url: str) -> str:
    """
    Extract Google Drive folder ID from URL.
    
    Args:
        url: Google Drive folder URL
        
    Returns:
        Folder ID string, or original string if no ID found
    """
    if not url:
        return url
    
    # If it's already just an ID, return as-is
    if not url.startswith('http'):
        return url
    
    # Pattern for Google Drive folder URLs
    patterns = [
        r'/folders/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            folder_id = match.group(1)
            logger.info(f"Extracted folder ID: {folder_id} from URL: {url[:50]}...")
            return folder_id
    
    logger.warning(f"Could not extract folder ID from URL: {url}")
    return url