"""
Git backup and rollback operations.

Provides:
- Pre-implementation backup (git tag creation)
- Rollback to previous state
- Backup verification
- Backup history tracking
"""

import subprocess
import os
from typing import Optional, Tuple
from datetime import datetime
import json


class BackupManager:
    """Manages git-based backups and rollbacks."""

    def __init__(self, repo_path: str = "."):
        """Initialize backup manager."""
        self.repo_path = repo_path

    def _run_git_command(self, command: str) -> Tuple[bool, str]:
        """Run git command and return success/output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            return False, str(e)

    def create_backup(self, cycle_number: int) -> Tuple[bool, str, Optional[str]]:
        """
        Create pre-implementation backup (git tag).

        Returns:
            (success: bool, commit_hash: str, error: Optional[str])
        """
        # Get current HEAD
        success, head = self._run_git_command("git rev-parse HEAD")
        if not success:
            return False, "", "Failed to get current git HEAD"

        commit_hash = head.strip()

        # Create backup tag
        tag_name = f"backup-cycle-{cycle_number}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        success, output = self._run_git_command(f"git tag {tag_name} {commit_hash}")
        if not success:
            return False, "", f"Failed to create git tag: {output}"

        return True, commit_hash, None

    def get_current_commit(self) -> Tuple[bool, str]:
        """Get current git HEAD commit hash."""
        success, output = self._run_git_command("git rev-parse HEAD")
        return success, output.strip() if success else ""

    def get_branch_name(self) -> Tuple[bool, str]:
        """Get current git branch name."""
        success, output = self._run_git_command("git rev-parse --abbrev-ref HEAD")
        return success, output.strip() if success else ""

    def rollback_to_commit(self, commit_hash: str) -> Tuple[bool, Optional[str]]:
        """
        Rollback to specific commit.

        Returns:
            (success: bool, error: Optional[str])
        """
        success, output = self._run_git_command(f"git reset --hard {commit_hash}")
        if not success:
            return False, f"Failed to rollback to {commit_hash}: {output}"
        return True, None

    def verify_backup_exists(self, tag_name: str) -> Tuple[bool, str]:
        """
        Verify backup tag exists and get its commit hash.

        Returns:
            (exists: bool, commit_hash: str)
        """
        success, output = self._run_git_command(f"git rev-list -n 1 {tag_name}")
        return success, output.strip() if success else ""

    def list_backup_tags(self) -> Tuple[bool, list]:
        """List all backup tags."""
        success, output = self._run_git_command("git tag -l 'backup-*'")
        if not success:
            return False, []
        tags = output.split("\n") if output else []
        return True, sorted(tags, reverse=True)

    def create_commit(
        self,
        message: str,
        files: Optional[list] = None,
        author_name: str = "Claude Code Agent",
        author_email: str = "agent@trade-alerts.local"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create git commit.

        Args:
            message: Commit message
            files: Optional list of files to stage (if None, stages all)
            author_name: Commit author name
            author_email: Commit author email

        Returns:
            (success: bool, commit_hash: str, error: Optional[str])
        """
        # Stage files
        if files:
            for file in files:
                success, _ = self._run_git_command(f"git add {file}")
                if not success:
                    return False, "", f"Failed to stage {file}"
        else:
            success, _ = self._run_git_command("git add -A")
            if not success:
                return False, "", "Failed to stage changes"

        # Check if there are changes to commit
        success, output = self._run_git_command("git status --short")
        if not success or not output:
            return False, "", "No changes to commit"

        # Create commit with author info
        env_vars = f'GIT_AUTHOR_NAME="{author_name}" GIT_AUTHOR_EMAIL="{author_email}" '
        success, output = self._run_git_command(
            f'{env_vars}git commit -m "{message}"'
        )
        if not success:
            return False, "", f"Failed to create commit: {output}"

        # Get commit hash
        success, commit_hash = self._run_git_command("git rev-parse HEAD")
        if not success:
            return False, "", "Failed to get commit hash"

        return True, commit_hash.strip(), None

    def get_diff_stats(self, commit1: str, commit2: str = "HEAD") -> Tuple[bool, dict]:
        """
        Get diff statistics between two commits.

        Returns:
            (success: bool, stats: dict with insertions, deletions, files_changed)
        """
        success, output = self._run_git_command(f"git diff --stat {commit1}..{commit2}")
        if not success:
            return False, {}

        stats = {
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
            "raw_output": output
        }

        # Parse output (format: "file.py | 10 +++++-----")
        lines = output.split("\n")
        for line in lines:
            if "|" in line and ("+" in line or "-" in line):
                stats["files_changed"] += 1
                # Count + and - signs
                parts = line.split("|")
                if len(parts) > 1:
                    changes = parts[1].strip()
                    stats["insertions"] += changes.count("+")
                    stats["deletions"] += changes.count("-")

        return True, stats

    def get_changes_for_files(self, files: list, since_commit: Optional[str] = None) -> dict:
        """
        Get detailed changes for specific files.

        Returns:
            Dict with file paths as keys, changes as values
        """
        changes = {}
        for file in files:
            if since_commit:
                cmd = f"git diff {since_commit}..HEAD -- {file}"
            else:
                cmd = f"git diff HEAD -- {file}"

            success, output = self._run_git_command(cmd)
            if success:
                changes[file] = output

        return changes

    def cleanup_old_backups(self, keep_last_n: int = 10) -> Tuple[bool, list]:
        """
        Delete old backup tags, keeping only last N.

        Returns:
            (success: bool, deleted_tags: list)
        """
        success, tags = self.list_backup_tags()
        if not success or len(tags) <= keep_last_n:
            return True, []

        deleted = []
        for tag in tags[keep_last_n:]:
            success, _ = self._run_git_command(f"git tag -d {tag}")
            if success:
                deleted.append(tag)

        return True, deleted

    def export_state_to_file(self, output_file: str) -> Tuple[bool, Optional[str]]:
        """
        Export git state information to JSON file.

        Returns:
            (success: bool, error: Optional[str])
        """
        try:
            success, branch = self.get_branch_name()
            if not success:
                return False, f"Failed to get branch: {branch}"

            success, commit = self.get_current_commit()
            if not success:
                return False, f"Failed to get current commit: {commit}"

            success, tags = self.list_backup_tags()
            if not success:
                tags = []

            state = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "branch": branch,
                "commit_hash": commit,
                "backup_tags": tags[:10]  # Last 10 backups
            }

            with open(output_file, "w") as f:
                json.dump(state, f, indent=2)

            return True, None
        except Exception as e:
            return False, str(e)


# Global backup manager instance
_backup_manager_instance: Optional[BackupManager] = None


def get_backup_manager(repo_path: str = ".") -> BackupManager:
    """Get or create global backup manager instance."""
    global _backup_manager_instance
    if _backup_manager_instance is None:
        _backup_manager_instance = BackupManager(repo_path)
    return _backup_manager_instance
