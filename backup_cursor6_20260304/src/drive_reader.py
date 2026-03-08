"""Read analysis files from Google Drive"""

import os
import re
import json
import stat
from typing import List, Dict, Optional
from dotenv import load_dotenv
from src.logger import setup_logger

load_dotenv()

try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    from oauth2client.client import OAuth2Credentials
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False
    print("Warning: PyDrive2 not installed. Install with: pip install PyDrive2")

logger = setup_logger()

class DriveReader:
    """Read files from Google Drive folder"""
    
    def __init__(self, folder_id: str):
        """
        Initialize Drive reader
        
        Args:
            folder_id: Google Drive folder ID containing analysis files
                      (can be full URL or just the ID)
        """
        # Extract folder ID from URL if needed.
        # Handles formats like:
        #   https://drive.google.com/drive/folders/1xlsxAV7dim4NubUNK8fCIuARF_iVPFEC?usp=drive_link
        #   https://drive.google.com/open?id=1xlsxAV7dim4NubUNK8fCIuARF_iVPFEC
        #   1xlsxAV7dim4NubUNK8fCIuARF_iVPFEC  (raw ID)
        if 'drive.google.com' in folder_id:
            match = re.search(r'/folders/([a-zA-Z0-9_-]+)', folder_id)
            if match:
                self.folder_id = match.group(1)
            else:
                match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', folder_id)
                self.folder_id = match.group(1) if match else folder_id
        else:
            # Strip any stray query parameters from a raw ID
            self.folder_id = folder_id.split('?')[0].split('&')[0]
        self.drive = None
        self.enabled = False
        self._temp_credential_files = []  # Track temporary credential files for cleanup
        
        if not DRIVE_AVAILABLE:
            logger.error("PyDrive2 not available")
            return
        
        try:
            self._authenticate()
            self.enabled = True
            logger.info(f"✅ Drive reader initialized for folder: {self.folder_id[:20]}...")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Drive reader: {e}")
            logger.error(f"   Folder ID: {self.folder_id}")
            logger.error(f"   Check: GOOGLE_DRIVE_REFRESH_TOKEN and GOOGLE_DRIVE_CREDENTIALS_JSON are set correctly")
            self.enabled = False

    def _mask_secret(self, value: str, visible_chars: int = 6) -> str:
        """Return a masked version of a secret for safe logging"""
        if not value:
            return '(empty)'
        if len(value) <= visible_chars:
            return '***'
        return f"{value[:visible_chars]}...***"

    def _save_new_refresh_token(self, new_token: str):
        """Persist a rotated refresh token so the next startup can use it"""
        # Try persistent disk first (Render), then local data dir
        candidates = []
        if os.path.exists('/var/data'):
            candidates.append('/var/data/new_refresh_token.txt')
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        candidates.append(os.path.join(data_dir, 'new_refresh_token.txt'))

        for path in candidates:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(new_token)
                self._set_secure_permissions(path)
                logger.info(f"New refresh token saved to {path}")
                logger.warning("ACTION REQUIRED: Update GOOGLE_DRIVE_REFRESH_TOKEN env var with the new token in the saved file")
                return
            except Exception as e:
                logger.warning(f"Could not save new refresh token to {path}: {e}")

    def _load_saved_refresh_token(self) -> str:
        """Load a previously saved rotated refresh token, if one exists"""
        candidates = []
        if os.path.exists('/var/data'):
            candidates.append('/var/data/new_refresh_token.txt')
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        candidates.append(os.path.join(data_dir, 'new_refresh_token.txt'))

        for path in candidates:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        token = f.read().strip()
                    if token:
                        logger.info(f"Loaded saved refresh token from {path}")
                        return token
            except Exception as e:
                logger.warning(f"Could not load saved refresh token from {path}: {e}")
        return ''

    def _set_secure_permissions(self, file_path: str):
        """Set file permissions to 0600 (owner read/write only)"""
        try:
            # On Unix-like systems, set file permissions to owner read/write only
            if os.name != 'nt':  # Not Windows
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
                logger.debug(f"Set secure permissions (0600) on {file_path}")
        except Exception as e:
            logger.warning(f"Could not set secure permissions on {file_path}: {e}")

    def _cleanup_credential_files(self):
        """Delete temporary credential files created during authentication"""
        for file_path in self._temp_credential_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up credential file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete credential file {file_path}: {e}")
        self._temp_credential_files.clear()

    def _authenticate(self):
        """Authenticate with Google Drive"""
        refresh_token = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')

        # CRITICAL: Convert credentials file path to absolute path
        # If env var is set, convert relative paths to absolute using /var/data as base
        # This fixes the "credentials.json not found" error when working directory changes
        creds_file_env = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE', '')
        if creds_file_env:
            # Convert to absolute path if relative
            if os.path.isabs(creds_file_env):
                credentials_file = creds_file_env
            else:
                # Relative path - make absolute using /var/data on Render, current dir locally
                base_dir = '/var/data' if os.path.exists('/var/data') else os.getcwd()
                credentials_file = os.path.join(base_dir, creds_file_env)
        else:
            # No env var - use default in /var/data (Render) or current directory (local)
            default_creds_dir = '/var/data' if os.path.exists('/var/data') else os.getcwd()
            credentials_file = os.path.join(default_creds_dir, 'credentials.json')

        credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS_JSON', '')

        # Use a previously saved rotated token if available (takes priority over env var)
        saved_token = self._load_saved_refresh_token()
        if saved_token:
            refresh_token = saved_token

        # Debug logging
        if not refresh_token:
            logger.error("GOOGLE_DRIVE_REFRESH_TOKEN is empty or not set")
        elif len(refresh_token) < 50:
            logger.warning(f"Refresh token seems too short (length: {len(refresh_token)})")
        
        if not credentials_json:
            logger.error("GOOGLE_DRIVE_CREDENTIALS_JSON is empty or not set")
        
        if refresh_token and credentials_json:
            # ALWAYS create credentials.json from environment variable (overwrite any cached version)
            # This MUST be done BEFORE GoogleAuth() is called, as it looks for client_secrets.json by default
            # SECURITY: These files will be cleaned up after authentication
            try:
                creds_data = json.loads(credentials_json)
                with open(credentials_file, 'w') as f:
                    json.dump(creds_data, f)
                # Set secure file permissions (owner read/write only)
                self._set_secure_permissions(credentials_file)
                self._temp_credential_files.append(credentials_file)
                logger.info(f"Created temporary {credentials_file} with secure permissions")
            except Exception as e:
                logger.error(f"Failed to create {credentials_file}: {e}")
                self._cleanup_credential_files()
                raise

            # Also create client_secrets.json as alias (pydrive2 looks for this by default)
            # ALWAYS overwrite to ensure we use the latest credentials
            # Use same directory as credentials_file to ensure file is found during token refresh
            client_secrets_dir = os.path.dirname(credentials_file) or '.'
            client_secrets_file = os.path.join(client_secrets_dir, 'client_secrets.json')
            try:
                creds_data = json.loads(credentials_json)
                with open(client_secrets_file, 'w') as f:
                    json.dump(creds_data, f)
                # Set secure file permissions (owner read/write only)
                self._set_secure_permissions(client_secrets_file)
                self._temp_credential_files.append(client_secrets_file)
                logger.debug(f"Created temporary {client_secrets_file} with secure permissions")
            except Exception as e:
                logger.warning(f"Could not create {client_secrets_file}: {e}")
                self._cleanup_credential_files()
                # Don't raise here, client_secrets.json is optional
            
            # Load credentials
            with open(credentials_file, 'r') as f:
                creds_data = json.load(f)

            # Handle both "installed" (Desktop) and "web" (Web application) credential formats
            installed = creds_data.get('installed', {})
            web = creds_data.get('web', {})
            # Try installed first, then web, then root level
            client_id = installed.get('client_id') or web.get('client_id') or creds_data.get('client_id')
            client_secret = installed.get('client_secret') or web.get('client_secret') or creds_data.get('client_secret')

            if client_id and client_secret:
                credentials = OAuth2Credentials(
                    None,  # access_token (will be refreshed)
                    client_id,
                    client_secret,
                    refresh_token,
                    None,  # token_expiry
                    'https://oauth2.googleapis.com/token',  # token_uri
                    'Trade Alerts',  # user_agent
                    revoke_uri=None,
                    id_token=None,
                    token_response=None,
                    scopes=['https://www.googleapis.com/auth/drive'],
                    token_info_uri=None
                )

                # Initialize GoogleAuth with in-memory settings dict.
                # Passing settings dict directly to GoogleAuth() skips settings.yaml loading,
                # ensuring settings are always consistent with environment variables.
                explicit_settings = {
                    'client_config_backend': 'settings',
                    'client_config': {
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                        'token_uri': 'https://oauth2.googleapis.com/token',
                        'revoke_uri': 'https://oauth2.googleapis.com/revoke',
                        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                    },
                    'save_credentials': False,
                    'get_refresh_token': True,
                    'oauth_scope': ['https://www.googleapis.com/auth/drive'],
                }
                logger.debug("Initializing GoogleAuth with explicit in-memory settings")
                gauth = GoogleAuth(settings=explicit_settings)
                logger.debug(
                    f"GoogleAuth settings enforced: save_credentials=False, "
                    f"client_config_backend=settings, client_id={self._mask_secret(client_id)}"
                )

                # Set credentials directly (don't use LoadCredentialsFile as it may cause module errors)
                gauth.credentials = credentials
                # Refresh to get access token
                try:
                    old_refresh_token = refresh_token
                    gauth.Refresh()

                    # CRITICAL: Google may return a NEW refresh token when refreshing
                    # If a new refresh token is returned, the old one is invalidated
                    new_refresh_token = gauth.credentials.refresh_token
                    if new_refresh_token and new_refresh_token != old_refresh_token:
                        logger.warning("=" * 80)
                        logger.warning("⚠️  Google returned a NEW refresh token!")
                        logger.warning("   Your OLD refresh token in GOOGLE_DRIVE_REFRESH_TOKEN is now INVALID")
                        logger.warning("   The new token has been saved to disk for use until the env var is updated.")
                        logger.warning("   Update GOOGLE_DRIVE_REFRESH_TOKEN in Render Dashboard → Environment")
                        logger.warning("=" * 80)
                        # Persist the new token so the next restart uses it automatically
                        self._save_new_refresh_token(new_refresh_token)

                    # Do NOT call SaveCredentialsFile() — with save_credentials: False,
                    # PyDrive2 does not manage token persistence. The refresh token env var
                    # is the source of truth. Token rotation is handled by _save_new_refresh_token().
                    logger.info("✅ OAuth2 authenticated using refresh token (in-memory)")
                    self.drive = GoogleDrive(gauth)

                    # NOTE: credentials.json and client_secrets.json remain on disk in /var/data/
                    # as a defensive measure, but the auth flow no longer depends on them.
                    # PyDrive2 is configured to use in-memory credentials (save_credentials: False,
                    # client_config_backend: settings), so file presence/absence does not affect operation.
                except Exception as refresh_error:
                    error_msg = str(refresh_error)
                    logger.error(f"Failed to refresh token: {refresh_error}")
                    logger.error(f"Error type: {type(refresh_error).__name__}")
                    logger.error(f"Client ID: {self._mask_secret(client_id)}")
                    logger.error(f"Client Secret: ***REDACTED*** (length: {len(client_secret)})")
                    logger.error(f"Refresh Token: {self._mask_secret(refresh_token)} (length: {len(refresh_token)})")
                    # Check for specific error types
                    if 'invalid_client' in error_msg.lower() or 'invalid_grant' in error_msg.lower():
                        logger.error("⚠️ This usually means Client ID/Secret or Refresh Token mismatch")
                        logger.error("   Make sure refresh token was generated with the SAME Client ID/Secret")

                    # Clean up credential files on error
                    self._cleanup_credential_files()
                    raise
            else:
                self._cleanup_credential_files()
                raise ValueError("Missing client_id or client_secret")
        else:
            self._cleanup_credential_files()
            raise ValueError("GOOGLE_DRIVE_REFRESH_TOKEN and GOOGLE_DRIVE_CREDENTIALS_JSON required")
    
    def list_files(self) -> List[Dict]:
        """
        List all files in the folder
        
        Returns:
            List of file metadata dictionaries
        """
        if not self.enabled or not self.drive:
            logger.error("Drive reader not enabled")
            return []
        
        try:
            file_list = self.drive.ListFile({
                'q': f"'{self.folder_id}' in parents and trashed=false"
            }).GetList()
            
            files = []
            for file in file_list:
                files.append({
                    'id': file['id'],
                    'title': file['title'],
                    'modifiedDate': file['modifiedDate'],
                    'mimeType': file['mimeType']
                })
            
            logger.info(f"Found {len(files)} files in folder")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def download_file(self, file_id: str, file_name: str) -> Optional[str]:
        """
        Download a file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            file_name: Local filename to save as
            
        Returns:
            Path to downloaded file, or None if failed
        """
        if not self.enabled or not self.drive:
            return None

        # Sanitize filename to prevent path traversal (file_name comes from Google Drive metadata)
        safe_name = os.path.basename(file_name)
        if not safe_name or safe_name in ('.', '..'):
            logger.error(f"Invalid filename from Drive: {file_name!r}")
            return None

        try:
            file_drive = self.drive.CreateFile({'id': file_id})

            # Create data directory if needed
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)

            download_path = os.path.join(data_dir, safe_name)
            file_drive.GetContentFile(download_path)

            logger.info(f"Downloaded {safe_name}")
            return download_path
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None
    
    def get_latest_analysis_files(self, pattern: str = None) -> List[Dict]:
        """
        Get the latest analysis files (sorted by modification date)
        
        Args:
            pattern: Optional filename pattern to filter (e.g., 'summary', 'report')
            
        Returns:
            List of file metadata, sorted by modification date (newest first)
        """
        files = self.list_files()
        
        # Filter by pattern if provided
        if pattern:
            files = [f for f in files if pattern.lower() in f['title'].lower()]
        
        # Sort by modification date (newest first)
        files.sort(key=lambda x: x['modifiedDate'], reverse=True)
        
        return files

