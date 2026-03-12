"""
Log Backup Agent - Modular System Foundation (FIXED: Pulls from Render API)

This agent runs every 15 minutes and backs up log files from:
- Scalp-Engine service: Fetched via https://config-api-8n37.onrender.com/logs/engine
- OANDA logs: Fetched via https://config-api-8n37.onrender.com/logs/oanda
- Scalp-Engine UI: Fetched via https://config-api-8n37.onrender.com/logs/ui
- Trade-Alerts service: Fetched from local logs directory

Backups are stored locally in logs_archive/ directory for offline analysis.

Usage:
    python agents/log_backup_agent.py
"""

import os
import sys
import shutil
import logging
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
import glob

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - LogBackupAgent - %(levelname)s - %(message)s'
)
logger = logging.getLogger('LogBackupAgent')

# Render Config API for accessing logs
CONFIG_API_BASE_URL = "https://config-api-8n37.onrender.com"
CONFIG_API_LOGS_ENDPOINT = f"{CONFIG_API_BASE_URL}/logs"


class LogBackupAgent:
    """
    Backs up log files from Render services to a local archive directory.

    Fetches logs from:
    - Scalp-Engine Config API (served from /var/data/logs/ on Render)
    - Trade-Alerts (via local logs directory)

    This is the foundation of a modular agent system.
    """

    def __init__(self, base_dir: str = None):
        """
        Initialize the backup agent.

        Args:
            base_dir: Base directory for Trade-Alerts project. Defaults to parent of agents/.
        """
        if base_dir is None:
            base_dir = str(Path(__file__).parent.parent)

        self.base_dir = Path(base_dir)
        self.archive_dir = self.base_dir / "logs_archive"
        self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d")

        # Session log for tracking this backup run
        self.session_dir = self.archive_dir / "sessions" / self.session_id
        self.session_log = self.session_dir / f"backup_{self.timestamp}.json"

        # Log sources configuration
        self.log_sources = {
            "Scalp-Engine": {
                "type": "api",
                "endpoint": f"{CONFIG_API_LOGS_ENDPOINT}/engine",
                "archive_dir": self.archive_dir / "Scalp-Engine",
                "filename": "scalp_engine_{}.log"
            },
            "OANDA": {
                "type": "api",
                "endpoint": f"{CONFIG_API_LOGS_ENDPOINT}/oanda",
                "archive_dir": self.archive_dir / "Scalp-Engine",
                "filename": "oanda_trades_{}.log"
            },
            "Scalp-Engine-UI": {
                "type": "api",
                "endpoint": f"{CONFIG_API_LOGS_ENDPOINT}/ui",
                "archive_dir": self.archive_dir / "Scalp-Engine",
                "filename": "scalp_ui_{}.log"
            },
            "Trade-Alerts": {
                "type": "local",
                "local_dir": self.base_dir / "logs",
                "archive_dir": self.archive_dir / "Trade-Alerts",
                "patterns": ["trade_alerts_*.log"]
            }
        }

        self.backup_stats = {
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "files_backed_up": 0,
            "files_skipped": 0,
            "errors": [],
            "sources": {}
        }

    def setup_directories(self) -> bool:
        """Create archive directories if they don't exist."""
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            self.session_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories for each source
            for source_name, source_config in self.log_sources.items():
                archive_dir = source_config.get("archive_dir")
                if archive_dir:
                    archive_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"📁 Archive directory: {self.archive_dir}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create archive directory: {e}")
            self.backup_stats["errors"].append(f"Directory creation: {str(e)}")
            return False

    def fetch_log_from_api(self, source_name: str, api_endpoint: str, archive_dir: Path, filename_template: str) -> int:
        """
        Fetch log content from Render Config API.

        Args:
            source_name: Name of the source (e.g., 'Scalp-Engine')
            api_endpoint: Full API endpoint URL
            archive_dir: Directory to save the log to
            filename_template: Template for filename with {} for date

        Returns:
            Number of files backed up (0 or 1)
        """
        try:
            logger.info(f"  📡 Fetching {source_name} logs from API...")

            response = requests.get(api_endpoint, timeout=10)
            response.raise_for_status()

            log_content = response.text
            if not log_content or log_content.strip() == "":
                logger.warning(f"  ⚠️ {source_name} API returned empty content")
                return 0

            # Generate filename
            date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
            filename = filename_template.format(date_str)
            backup_filename = f"{self.timestamp}_{filename}"
            archive_path = archive_dir / backup_filename

            # Ensure archive directory exists
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(archive_path, 'w', encoding='utf-8') as f:
                f.write(log_content)

            file_size = len(log_content)
            logger.info(f"  ✅ Backed up {source_name}: {backup_filename} ({file_size} bytes)")
            return 1

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error (Render service may be sleeping): {source_name}"
            logger.warning(f"  ⚠️ {error_msg}")
            self.backup_stats["errors"].append(error_msg)
            return 0
        except requests.exceptions.Timeout:
            error_msg = f"Timeout fetching {source_name} (API endpoint may be unavailable)"
            logger.warning(f"  ⚠️ {error_msg}")
            self.backup_stats["errors"].append(error_msg)
            return 0
        except Exception as e:
            error_msg = f"Failed to fetch {source_name}: {str(e)}"
            logger.error(f"  ❌ {error_msg}")
            self.backup_stats["errors"].append(error_msg)
            return 0

    def backup_logs(self) -> bool:
        """
        Back up all log files from Render services and local sources.

        Returns:
            True if backup completed (even with partial success)
        """
        logger.info("🔄 Starting log backup cycle...")

        for source_name, source_config in self.log_sources.items():
            logger.info(f"Processing {source_name}...")

            self.backup_stats["sources"][source_name] = {
                "files_found": 0,
                "files_backed_up": 0,
                "files_skipped": 0,
            }

            # Handle API-based sources
            if source_config["type"] == "api":
                files_backed_up = self.fetch_log_from_api(
                    source_name,
                    source_config["endpoint"],
                    source_config["archive_dir"],
                    source_config["filename"]
                )
                self.backup_stats["sources"][source_name]["files_found"] = 1 if files_backed_up else 0
                self.backup_stats["sources"][source_name]["files_backed_up"] = files_backed_up
                self.backup_stats["files_backed_up"] += files_backed_up

            # Handle local file sources (Trade-Alerts)
            elif source_config["type"] == "local":
                local_dir = source_config["local_dir"]
                archive_dir = source_config["archive_dir"]
                patterns = source_config.get("patterns", [])

                if not local_dir.exists():
                    logger.warning(f"  ⚠️ Local directory not found: {local_dir}")
                    continue

                for pattern in patterns:
                    matching_files = glob.glob(str(local_dir / pattern))
                    # Prefer most recent by mtime so we back up today's log first
                    matching_files = sorted(matching_files, key=lambda p: os.path.getmtime(p), reverse=True)
                    self.backup_stats["sources"][source_name]["files_found"] = len(matching_files)

                    for file_path in matching_files:
                        if self._backup_file(file_path, source_name, archive_dir):
                            self.backup_stats["sources"][source_name]["files_backed_up"] += 1
                            self.backup_stats["files_backed_up"] += 1

        return True

    def _backup_file(self, file_path: str, source_name: str, archive_dir: Path) -> bool:
        """
        Back up a single log file.

        Returns:
            True if file was backed up, False if skipped or failed
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return False

            # Destination path (keep filename, add timestamp prefix)
            dest_file = archive_dir / f"{self.timestamp}_{file_path.name}"

            # Skip if file already backed up in this session
            if dest_file.exists():
                logger.debug(f"  ⏭️ Skipped (already backed up): {file_path.name}")
                self.backup_stats["sources"][source_name]["files_skipped"] += 1
                self.backup_stats["files_skipped"] += 1
                return False

            # Ensure archive directory exists
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(file_path, dest_file)

            file_size = file_path.stat().st_size
            logger.debug(f"  ✅ Backed up: {source_name}/{file_path.name} ({file_size} bytes)")
            return True

        except Exception as e:
            error_msg = f"File backup error ({file_path}): {str(e)}"
            logger.error(f"  ❌ {error_msg}")
            self.backup_stats["errors"].append(error_msg)
            return False

    def save_session_log(self) -> bool:
        """Save this backup session's statistics."""
        try:
            with open(self.session_log, 'w') as f:
                json.dump(self.backup_stats, f, indent=2)
            logger.info(f"📝 Session log saved: {self.session_log}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save session log: {e}")
            return False

    def print_summary(self):
        """Print backup summary."""
        logger.info("=" * 70)
        logger.info("📊 BACKUP SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total files backed up: {self.backup_stats['files_backed_up']}")
        logger.info(f"Total files skipped: {self.backup_stats['files_skipped']}")

        for source, stats in self.backup_stats["sources"].items():
            backed_up = stats['files_backed_up']
            skipped = stats['files_skipped']
            logger.info(f"  {source:20} → {backed_up} backed up, {skipped} skipped")

        if self.backup_stats["errors"]:
            logger.warning(f"⚠️ Errors encountered: {len(self.backup_stats['errors'])}")
            for error in self.backup_stats["errors"]:
                logger.warning(f"  - {error}")
        else:
            logger.info("✅ No errors")

        logger.info("=" * 70)

    def run(self) -> bool:
        """Execute the backup agent."""
        try:
            if not self.setup_directories():
                return False

            if not self.backup_logs():
                return False

            if not self.save_session_log():
                logger.warning("⚠️ Failed to save session log, but backup completed")

            self.print_summary()
            return True

        except Exception as e:
            logger.error(f"❌ Backup agent failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point for the backup agent."""
    # DISABLED GUARD: prevents backups and external API calls when toggled.
    # Re-enable by deleting .backup_disabled in the Trade-Alerts root and/or
    # clearing TRADE_ALERTS_BACKUP_DISABLED in the environment.
    base_dir = Path(__file__).parent.parent
    disabled_file = base_dir / ".backup_disabled"
    if disabled_file.exists() or os.environ.get("TRADE_ALERTS_BACKUP_DISABLED", "").strip() == "1":
        logger.info("=" * 70)
        logger.info("🔕 Log Backup Agent is DISABLED – no backup or API calls will run.")
        logger.info("    Remove .backup_disabled and TRADE_ALERTS_BACKUP_DISABLED to re-enable.")
        logger.info("=" * 70)
        return 0

    logger.info("=" * 70)
    logger.info("🔄 Log Backup Agent Starting")
    logger.info("=" * 70)

    agent = LogBackupAgent()

    try:
        success = agent.run()
        if success:
            logger.info("✅ Backup agent completed successfully")
            return 0
        else:
            logger.error("❌ Backup agent completed with errors")
            return 1
    except KeyboardInterrupt:
        logger.warning("⚠️ Backup agent interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
