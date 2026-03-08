"""
Test execution and coverage validation utility for Coding Expert Agent.

Handles:
- Running unit/integration tests
- Coverage validation (>90% requirement)
- Test output capture and parsing
- Test result aggregation
- Failure detection and reporting
"""

import subprocess
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class TestResult:
    """Represents test execution results."""

    def __init__(self):
        """Initialize test result."""
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.coverage_percent = 0.0
        self.output = ""
        self.errors = []
        self.success = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "coverage_percent": self.coverage_percent,
            "success": self.success,
            "errors": self.errors
        }


class TestRunner:
    """Executes tests and validates coverage."""

    def __init__(self, repo_root: str = "."):
        """
        Initialize test runner.

        Args:
            repo_root: Root directory of repository
        """
        self.repo_root = repo_root

    def run_test_file(self, test_file: str) -> TestResult:
        """
        Run a single test file.

        Args:
            test_file: Path to test file (relative to repo_root)

        Returns:
            TestResult object
        """
        result = TestResult()
        full_path = Path(self.repo_root) / test_file

        if not full_path.exists():
            result.errors.append(f"Test file not found: {test_file}")
            return result

        try:
            # Run pytest with coverage
            cmd = [
                "pytest",
                str(full_path),
                "-v",
                "--tb=short",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=json"
            ]

            process = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            result.output = process.stdout + "\n" + process.stderr
            result.success = process.returncode == 0

            # Parse output
            self._parse_pytest_output(result)

            # Parse coverage
            self._parse_coverage_report(result)

        except subprocess.TimeoutExpired:
            result.errors.append("Test execution timeout (>300s)")
            return result
        except Exception as e:
            result.errors.append(f"Test execution error: {e}")
            return result

        return result

    def run_test_directory(self, test_dir: str) -> TestResult:
        """
        Run all tests in a directory.

        Args:
            test_dir: Path to test directory (relative to repo_root)

        Returns:
            Aggregated TestResult
        """
        result = TestResult()
        full_path = Path(self.repo_root) / test_dir

        if not full_path.exists():
            result.errors.append(f"Test directory not found: {test_dir}")
            return result

        try:
            # Run pytest with coverage
            cmd = [
                "pytest",
                str(full_path),
                "-v",
                "--tb=short",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=json"
            ]

            process = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=600
            )

            result.output = process.stdout + "\n" + process.stderr
            result.success = process.returncode == 0

            # Parse output
            self._parse_pytest_output(result)

            # Parse coverage
            self._parse_coverage_report(result)

        except subprocess.TimeoutExpired:
            result.errors.append("Test execution timeout (>600s)")
            return result
        except Exception as e:
            result.errors.append(f"Test execution error: {e}")
            return result

        return result

    def run_python_module(self, module_path: str) -> TestResult:
        """
        Run a Python module with test runner.

        Args:
            module_path: Path to Python module (relative to repo_root)

        Returns:
            TestResult
        """
        result = TestResult()
        full_path = Path(self.repo_root) / module_path

        if not full_path.exists():
            result.errors.append(f"Module not found: {module_path}")
            return result

        try:
            # Run Python module directly
            cmd = ["python", str(full_path)]

            process = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            result.output = process.stdout + "\n" + process.stderr
            result.success = process.returncode == 0

            # Parse output for test counts
            self._parse_module_output(result)

        except subprocess.TimeoutExpired:
            result.errors.append("Module execution timeout (>300s)")
            return result
        except Exception as e:
            result.errors.append(f"Module execution error: {e}")
            return result

        return result

    def validate_coverage(self, result: TestResult, minimum: float = 90.0) -> bool:
        """
        Validate that coverage meets minimum threshold.

        Args:
            result: TestResult from test execution
            minimum: Minimum coverage percentage required (default: 90%)

        Returns:
            True if coverage meets threshold
        """
        if result.coverage_percent >= minimum:
            return True

        result.errors.append(
            f"Coverage {result.coverage_percent:.1f}% below minimum {minimum}%"
        )
        return False

    def _parse_pytest_output(self, result: TestResult) -> None:
        """Parse pytest output to extract test counts."""
        output = result.output

        # Look for test summary line (e.g., "passed 17 in 1.23s")
        match = re.search(r"(\d+) passed", output)
        if match:
            result.passed_tests = int(match.group(1))

        match = re.search(r"(\d+) failed", output)
        if match:
            result.failed_tests = int(match.group(1))

        match = re.search(r"(\d+) skipped", output)
        if match:
            result.skipped_tests = int(match.group(1))

        result.total_tests = result.passed_tests + result.failed_tests + result.skipped_tests

        # Extract errors if present
        if result.failed_tests > 0:
            # Extract failure details
            failure_section = re.search(r"FAILED (.*?)(?:=|$)", output, re.DOTALL)
            if failure_section:
                result.errors.append(failure_section.group(1)[:500])  # First 500 chars

    def _parse_coverage_report(self, result: TestResult) -> None:
        """Parse coverage report to extract percentage."""
        output = result.output

        # Try to find coverage percentage (e.g., "TOTAL ... 92%")
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            result.coverage_percent = float(match.group(1))
            return

        # Try alternate format (e.g., "Total coverage: 92%")
        match = re.search(r"(?:coverage|Coverage).*?(\d+(?:\.\d+)?)%", output)
        if match:
            result.coverage_percent = float(match.group(1))

    def _parse_module_output(self, result: TestResult) -> None:
        """Parse direct module execution output for test counts."""
        output = result.output

        # Look for PASS/FAIL indicators
        match = re.search(r"PASS.*?All (.*?) tests? passed", output, re.IGNORECASE)
        if match:
            test_count_str = match.group(1)
            # Handle "17" or "SEVENTEEN" format
            if test_count_str.isdigit():
                result.passed_tests = int(test_count_str)
            else:
                # Try to count by test lines
                result.passed_tests = len(re.findall(r"✅|OK", output))

        match = re.search(r"FAILED.*?(\d+) test", output, re.IGNORECASE)
        if match:
            result.failed_tests = int(match.group(1))

        result.total_tests = result.passed_tests + result.failed_tests

    def get_test_summary(self, result: TestResult) -> str:
        """
        Generate human-readable test summary.

        Args:
            result: TestResult object

        Returns:
            Summary string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("TEST EXECUTION SUMMARY")
        lines.append("=" * 70)
        lines.append(f"Total Tests:    {result.total_tests}")
        lines.append(f"Passed:         {result.passed_tests}")
        lines.append(f"Failed:         {result.failed_tests}")
        lines.append(f"Skipped:        {result.skipped_tests}")
        lines.append(f"Coverage:       {result.coverage_percent:.1f}%")
        lines.append(f"Status:         {'PASS' if result.success else 'FAIL'}")

        if result.errors:
            lines.append("")
            lines.append("ERRORS:")
            for error in result.errors:
                lines.append(f"  - {error}")

        lines.append("=" * 70)

        return "\n".join(lines)
