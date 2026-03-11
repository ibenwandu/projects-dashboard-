"""
Git tool - git operations for documentation updates.

Handles commits, status checks, and history for Emy documentation
and session logs.
"""

import logging
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger('GitTool')


class GitTool:
    """Tool for git operations."""

    def __init__(self, repo_path: str = 'C:\\Users\\user\\projects\\personal'):
        """Initialize git tool for a repository."""
        self.repo_path = Path(repo_path)
        self.logger = logging.getLogger('GitTool')

    def git_status(self) -> Optional[Dict[str, Any]]:
        """Get git repository status."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.error(f"git status failed: {result.stderr}")
                return None

            # Parse output: "M  file.txt" → modified, "?? file.txt" → untracked
            staged = []
            unstaged = []
            untracked = []

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                status = line[:2]
                filename = line[3:]

                if status.startswith('??'):
                    untracked.append(filename)
                elif status[0] in ['M', 'A', 'D']:
                    staged.append(filename)
                elif status[1] in ['M', 'D']:
                    unstaged.append(filename)

            return {
                'staged': staged,
                'unstaged': unstaged,
                'untracked': untracked,
                'has_changes': bool(staged or unstaged)
            }

        except Exception as e:
            self.logger.error(f"Error getting git status: {e}")
            return None

    def git_add(self, files: List[str]) -> bool:
        """Stage files for commit."""
        try:
            result = subprocess.run(
                ['git', 'add'] + files,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.error(f"git add failed: {result.stderr}")
                return False

            self.logger.info(f"Staged {len(files)} files")
            return True

        except Exception as e:
            self.logger.error(f"Error staging files: {e}")
            return False

    def git_commit(self, message: str) -> bool:
        """Commit staged changes."""
        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                if 'nothing to commit' in result.stdout:
                    self.logger.debug("No changes to commit")
                    return True
                else:
                    self.logger.error(f"git commit failed: {result.stderr}")
                    return False

            self.logger.info(f"Committed: {message[:50]}")
            return True

        except Exception as e:
            self.logger.error(f"Error committing changes: {e}")
            return False

    def git_log(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent commit history."""
        try:
            result = subprocess.run(
                ['git', 'log', f'--max-count={limit}', '--oneline'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.error(f"git log failed: {result.stderr}")
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split(' ', 1)
                if len(parts) == 2:
                    commits.append({
                        'hash': parts[0],
                        'message': parts[1]
                    })

            return commits

        except Exception as e:
            self.logger.error(f"Error getting git log: {e}")
            return []

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        status = self.git_status()
        if status is None:
            return False
        return status.get('has_changes', False)
