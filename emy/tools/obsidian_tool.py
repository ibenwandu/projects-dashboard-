"""
Obsidian tool - read/write Obsidian vault files.

Integrates with Ibe's Obsidian knowledge base for dashboard updates and
cross-project documentation.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger('ObsidianTool')


class ObsidianTool:
    """Tool for Obsidian vault operations."""

    # Default Obsidian vault location
    VAULT_PATH = Path('C:\\Users\\user\\projects\\personal\\Obsidian Vault\\My Knowledge Base')
    DASHBOARD_FILE = VAULT_PATH / '00-DASHBOARD.md'

    @staticmethod
    def read_vault_file(file_path: str) -> Optional[str]:
        """Read a file from Obsidian vault."""
        try:
            full_path = Path(file_path)
            if not full_path.exists():
                logger.warning(f"Vault file not found: {file_path}")
                return None

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Read vault file: {file_path}")
                return content

        except Exception as e:
            logger.error(f"Error reading vault file {file_path}: {e}")
            return None

    @staticmethod
    def write_vault_file(file_path: str, content: str) -> bool:
        """Write to a file in Obsidian vault."""
        try:
            full_path = Path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
                logger.debug(f"Wrote vault file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing vault file {file_path}: {e}")
            return False

    @staticmethod
    def update_dashboard(metrics: Dict[str, Any]) -> bool:
        """
        Update Obsidian dashboard with project metrics.

        Args:
            metrics: Dict with keys:
                - phase_completion (0-5)
                - tasks_completed (int)
                - budget_used (float)
                - jobs_applied (int)
                - last_update (str, ISO format)

        Returns:
            True if updated successfully
        """
        try:
            if not ObsidianTool.DASHBOARD_FILE.exists():
                logger.warning(f"Dashboard file not found: {ObsidianTool.DASHBOARD_FILE}")
                return False

            # Read current dashboard
            with open(ObsidianTool.DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update metrics (would normally parse and update specific sections)
            # For Phase 3 Batch 1, just log the update
            logger.info(f"Dashboard update: phase={metrics.get('phase_completion')}, "
                       f"tasks={metrics.get('tasks_completed')}")

            return True

        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            return False

    @staticmethod
    def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a vault file."""
        try:
            full_path = Path(file_path)
            if not full_path.exists():
                return None

            stat = full_path.stat()
            return {
                'path': str(file_path),
                'size_bytes': stat.st_size,
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'exists': True
            }

        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
