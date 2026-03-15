"""Configuration for sandbox and testing environments"""
import os
from typing import Optional


class SandboxConfig:
    """Configuration for sandbox Gmail testing"""

    ENABLED = os.getenv('SANDBOX_ENABLED', 'false').lower() == 'true'
    EMAIL = os.getenv('SANDBOX_EMAIL', 'emy.test@gmail.com')
    SERVICE_ACCOUNT_JSON = os.getenv('SANDBOX_SERVICE_ACCOUNT_JSON')

    @staticmethod
    def is_configured() -> bool:
        """Check if sandbox is properly configured"""
        return SandboxConfig.ENABLED and SandboxConfig.SERVICE_ACCOUNT_JSON is not None

    @staticmethod
    def get_email() -> Optional[str]:
        """Get sandbox email if configured"""
        if SandboxConfig.is_configured():
            return SandboxConfig.EMAIL
        return None


class TestConfig:
    """General test configuration"""

    # Email testing
    SANDBOX_ENABLED = SandboxConfig.is_configured()
    SANDBOX_EMAIL = SandboxConfig.get_email()

    # Mock Gmail settings
    MOCK_EMAIL_DOMAIN = 'example.com'
    TEST_SENDER = f'test@{MOCK_EMAIL_DOMAIN}'

    # Timeouts
    EMAIL_TIMEOUT_SECONDS = 10
    POLLING_TIMEOUT_SECONDS = 30

    @staticmethod
    def skip_if_no_sandbox() -> bool:
        """Check if tests should skip due to missing sandbox config"""
        return not SandboxConfig.is_configured()
