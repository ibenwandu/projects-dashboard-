"""
Emy disable guard - emergency kill-switch mechanism.

File-based disable: presence of .emy_disabled disables Emy.
Environment-based disable: EMY_DISABLED=true env var disables Emy.
"""

import os
from pathlib import Path


class EMyDisableGuard:
    """Guard that checks if Emy should be disabled."""

    DISABLE_FILE = Path(__file__).parent.parent.parent / '.emy_disabled'
    DISABLE_ENV = 'EMY_DISABLED'

    def is_disabled(self) -> bool:
        """Check if Emy is disabled (file or env var)."""
        # Check file
        if self.DISABLE_FILE.exists():
            return True

        # Check environment variable
        if os.getenv(self.DISABLE_ENV, '').lower() == 'true':
            return True

        return False

    def set_disabled(self, disabled: bool):
        """Enable or disable Emy via file."""
        if disabled:
            self.DISABLE_FILE.touch()
        else:
            if self.DISABLE_FILE.exists():
                self.DISABLE_FILE.unlink()
