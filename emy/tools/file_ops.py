"""
File operations tool for Emy.

Utilities for reading, writing, and searching files.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from glob import glob

logger = logging.getLogger('FileOpsTool')


class FileOpsTool:
    """File operations wrapper."""

    @staticmethod
    def read_json_file(file_path: str) -> Optional[Dict]:
        """Read and parse JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                logger.debug(f"Read JSON: {file_path}")
                return data
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

    @staticmethod
    def write_json_file(file_path: str, data: Dict, pretty: bool = True) -> bool:
        """Write data to JSON file."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                if pretty:
                    json.dump(data, f, indent=2)
                else:
                    json.dump(data, f)
                logger.debug(f"Wrote JSON: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            return False

    @staticmethod
    def read_text_file(file_path: str) -> Optional[str]:
        """Read text file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                logger.debug(f"Read text: {file_path}")
                return content
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

    @staticmethod
    def write_text_file(file_path: str, content: str) -> bool:
        """Write text to file."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
                logger.debug(f"Wrote text: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            return False

    @staticmethod
    def list_files(directory: str, pattern: str = '*', recursive: bool = False) -> List[str]:
        """List files matching pattern."""
        try:
            if recursive:
                pattern = f"{directory}/**/{pattern}"
            else:
                pattern = f"{directory}/{pattern}"

            files = glob(pattern, recursive=recursive)
            logger.debug(f"Listed {len(files)} files matching {pattern}")
            return sorted(files)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(file_path)

    @staticmethod
    def get_file_size(file_path: str) -> Optional[int]:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return None
