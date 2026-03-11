"""
Skill loader - parses skill definitions from Markdown files.

Skills are defined as Markdown files with YAML frontmatter + sections.
"""

import logging
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger('SkillLoader')


class EMySkillLoader:
    """Loads skill definitions from Markdown files."""

    @staticmethod
    def parse_skill_markdown(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a skill definition from Markdown file.

        Expected format:
        ```
        ---
        name: skill_name
        domain: domain_name
        version: 1.0
        model: claude-haiku-4-5-20251001
        success_rate: 1.0
        ---

        ## Purpose
        ...

        ## Steps
        ...
        ```
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Parse frontmatter
            match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
            if not match:
                logger.error(f"Invalid skill format in {file_path}: missing frontmatter")
                return None

            frontmatter_text = match.group(1)
            body = match.group(2)

            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in {file_path}: {e}")
                return None

            # Parse sections
            sections = {}
            current_section = None
            current_content = []

            for line in body.split('\n'):
                if line.startswith('## '):
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = line[3:].strip()
                    current_content = []
                else:
                    current_content.append(line)

            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            # Combine frontmatter and sections
            skill_def = frontmatter.copy()
            skill_def['sections'] = sections

            logger.debug(f"Parsed skill: {skill_def.get('name')} v{skill_def.get('version')}")
            return skill_def

        except FileNotFoundError:
            logger.error(f"Skill file not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error parsing skill {file_path}: {e}")
            return None

    @staticmethod
    def load_skill(skill_name: str, skill_dir: str = 'emy/skills/definitions') -> Optional[Dict[str, Any]]:
        """
        Load a skill by name (looks for skill_name.md).

        Args:
            skill_name: Name of skill (without .md extension)
            skill_dir: Directory containing skill definitions

        Returns:
            Parsed skill definition or None if not found
        """
        skill_path = Path(skill_dir) / f"{skill_name}.md"

        if not skill_path.exists():
            logger.warning(f"Skill not found: {skill_path}")
            return None

        return EMySkillLoader.parse_skill_markdown(str(skill_path))
