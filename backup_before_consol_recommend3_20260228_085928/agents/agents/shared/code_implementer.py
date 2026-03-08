"""
Code implementation utilities for Coding Expert Agent.

Handles:
- Code file reading and modification
- Code change application
- Validation of changes
- Safety checks
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class CodeImplementer:
    """Implements code changes based on recommendations."""

    def __init__(self, repo_root: str = "."):
        """
        Initialize code implementer.

        Args:
            repo_root: Root directory of the repository
        """
        self.repo_root = repo_root

    def read_file(self, filepath: str) -> Optional[str]:
        """
        Read file contents.

        Args:
            filepath: Relative path from repo root

        Returns:
            File contents or None if file not found
        """
        full_path = Path(self.repo_root) / filepath
        try:
            with open(full_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None

    def write_file(self, filepath: str, content: str) -> bool:
        """
        Write file contents.

        Args:
            filepath: Relative path from repo root
            content: New file contents

        Returns:
            Success flag
        """
        full_path = Path(self.repo_root) / filepath
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False

    def apply_code_change(
        self,
        filepath: str,
        method: str,
        old_code: str,
        new_code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Apply a code change to a file.

        Args:
            filepath: Path to file
            method: Method/function name (for documentation)
            old_code: Code to replace (must be unique)
            new_code: Replacement code

        Returns:
            (success: bool, error: Optional[str])
        """
        # Read file
        content = self.read_file(filepath)
        if not content:
            return False, f"File not found: {filepath}"

        # Check if old code exists and is unique
        if old_code not in content:
            return False, f"Old code not found in {filepath}::{method}"

        count = content.count(old_code)
        if count > 1:
            return False, f"Old code appears {count} times in {filepath} (not unique)"

        # Replace code
        new_content = content.replace(old_code, new_code)

        # Write file
        if not self.write_file(filepath, new_content):
            return False, f"Failed to write {filepath}"

        return True, None

    def validate_change(
        self,
        filepath: str,
        expected_code: str
    ) -> bool:
        """
        Validate that a code change was applied correctly.

        Args:
            filepath: Path to file
            expected_code: Code that should be present

        Returns:
            True if code is present
        """
        content = self.read_file(filepath)
        if not content:
            return False

        return expected_code in content

    def find_method_location(self, filepath: str, method_name: str) -> Optional[int]:
        """
        Find line number where a method is defined.

        Args:
            filepath: Path to file
            method_name: Method name to find

        Returns:
            Line number (1-indexed) or None if not found
        """
        content = self.read_file(filepath)
        if not content:
            return None

        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Look for function/method definition
            if re.search(rf'^\s*def\s+{method_name}\s*\(', line):
                return i + 1  # 1-indexed

        return None

    def get_method_code(self, filepath: str, method_name: str) -> Optional[str]:
        """
        Extract a complete method from a file.

        Args:
            filepath: Path to file
            method_name: Method name

        Returns:
            Method code or None if not found
        """
        content = self.read_file(filepath)
        if not content:
            return None

        lines = content.split('\n')

        # Find method start
        start_line = None
        for i, line in enumerate(lines):
            if re.search(rf'^\s*def\s+{method_name}\s*\(', line):
                start_line = i
                break

        if start_line is None:
            return None

        # Find method end (next method or class definition at same indentation)
        base_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        end_line = len(lines)

        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # Skip empty lines
                continue

            # Check if we've hit another definition at same level
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= base_indent and (line.lstrip().startswith('def ') or
                                               line.lstrip().startswith('class ')):
                end_line = i
                break

        return '\n'.join(lines[start_line:end_line])

    def count_syntax_errors(self, filepath: str) -> int:
        """
        Count potential syntax errors in a Python file.

        Args:
            filepath: Path to file

        Returns:
            Number of syntax errors found
        """
        content = self.read_file(filepath)
        if not content:
            return 0

        errors = 0

        # Check for unmatched brackets
        bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        bracket_counts = {'{': 0, '[': 0, '(': 0}

        for char in content:
            if char in bracket_counts:
                bracket_counts[char] += 1
            elif char in bracket_pairs.values():
                for open_char, close_char in bracket_pairs.items():
                    if char == close_char:
                        bracket_counts[open_char] -= 1
                        if bracket_counts[open_char] < 0:
                            errors += 1

        # Check for unmatched quotes
        single_quote_count = 0
        double_quote_count = 0

        in_triple_single = False
        in_triple_double = False

        i = 0
        while i < len(content):
            # Check for triple quotes
            if i + 2 < len(content):
                if content[i:i+3] == '"""':
                    in_triple_double = not in_triple_double
                    i += 3
                    continue
                elif content[i:i+3] == "'''":
                    in_triple_single = not in_triple_single
                    i += 3
                    continue

            # Count single/double quotes
            if not in_triple_single and not in_triple_double:
                if content[i] == '"' and (i == 0 or content[i-1] != '\\'):
                    double_quote_count += 1
                elif content[i] == "'" and (i == 0 or content[i-1] != '\\'):
                    single_quote_count += 1

            i += 1

        if single_quote_count % 2 != 0:
            errors += 1
        if double_quote_count % 2 != 0:
            errors += 1

        return errors

    def apply_multiple_changes(
        self,
        filepath: str,
        changes: List[Dict[str, str]]
    ) -> Tuple[bool, List[str]]:
        """
        Apply multiple code changes to the same file.

        Args:
            filepath: Path to file
            changes: List of {old_code, new_code} dicts

        Returns:
            (success: bool, errors: List[str])
        """
        errors = []

        # Read file once
        content = self.read_file(filepath)
        if not content:
            return False, [f"File not found: {filepath}"]

        # Validate all changes before applying any
        for i, change in enumerate(changes):
            old_code = change.get("old_code", "")
            if old_code not in content:
                errors.append(f"Change {i}: Old code not found")
            elif content.count(old_code) > 1:
                errors.append(f"Change {i}: Old code not unique")

        if errors:
            return False, errors

        # Apply all changes
        new_content = content
        for change in changes:
            old_code = change.get("old_code", "")
            new_code = change.get("new_code", "")
            new_content = new_content.replace(old_code, new_code)

        # Write file
        if not self.write_file(filepath, new_content):
            return False, [f"Failed to write {filepath}"]

        return True, []

    def backup_file(self, filepath: str) -> Optional[str]:
        """
        Create a backup of a file.

        Args:
            filepath: Path to file

        Returns:
            Backup path or None if failed
        """
        content = self.read_file(filepath)
        if not content:
            return None

        backup_path = f"{filepath}.backup"
        if self.write_file(backup_path, content):
            return backup_path

        return None

    def get_file_stats(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics about a file.

        Args:
            filepath: Path to file

        Returns:
            Stats dict or None if file not found
        """
        content = self.read_file(filepath)
        if not content:
            return None

        lines = content.split('\n')
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]

        return {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "functions": len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE)),
            "classes": len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
        }
