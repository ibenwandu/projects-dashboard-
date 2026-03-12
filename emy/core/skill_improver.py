"""
Skill self-improvement engine.

Monitors skill outcomes, identifies underperforming skills, and auto-generates improvements.
Implements versioning and automatic rollback on failure.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import re

logger = logging.getLogger('SkillImprover')


class EMySkillImprover:
    """Improves skills based on success rate monitoring."""

    def __init__(self, db, skill_loader, skill_registry, notification_tool):
        """Initialize skill improver."""
        self.db = db
        self.skill_loader = skill_loader
        self.skill_registry = skill_registry
        self.notification_tool = notification_tool
        self.logger = logging.getLogger('SkillImprover')
        self.min_success_rate = 0.80
        self.min_runs_before_improve = 5
        self.rollback_threshold = 0.70

    def find_underperforming_skills(self) -> list:
        """Find skills with success_rate < min_success_rate."""
        underperformers = []

        try:
            # Get all registered skills
            all_skills = self.skill_registry.list_all()

            for skill_name in all_skills:
                skill = self.skill_registry.get(skill_name)
                if not skill:
                    continue

                # Get recent success rate
                success_rate = self.db.get_skill_success_rate(skill_name, self.min_runs_before_improve)

                # Check if underperforming
                if success_rate < self.min_success_rate:
                    underperformers.append({
                        'name': skill_name,
                        'version': skill.get('version', '1.0'),
                        'success_rate': success_rate,
                        'runs': self.min_runs_before_improve
                    })
                    self.logger.warning(
                        f"[IMPROVE] Found underperformer: {skill_name} v{skill.get('version', '1.0')} "
                        f"({success_rate:.1%})"
                    )

            return underperformers

        except Exception as e:
            self.logger.error(f"[IMPROVE] Error finding underperformers: {e}")
            return []

    def improve_skill(self, skill_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Improve a skill by generating new version.

        Args:
            skill_name: Name of skill to improve

        Returns:
            (success, result_dict)
        """
        try:
            # Get current skill
            current_skill = self.skill_registry.get(skill_name)
            if not current_skill:
                return False, {'error': f'Skill not found: {skill_name}'}

            old_version = current_skill.get('version', '1.0')
            old_success_rate = self.db.get_skill_success_rate(skill_name, self.min_runs_before_improve)

            self.logger.info(f"[IMPROVE] Starting improvement: {skill_name} v{old_version} ({old_success_rate:.1%})")

            # Back up current version
            backup_path = self._backup_skill(skill_name, old_version)
            if not backup_path:
                return False, {'error': 'Failed to backup current skill'}

            # Generate improved version
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

                improvement_prompt = self._build_improvement_prompt(skill_name, current_skill, old_success_rate)

                response = client.messages.create(
                    model='claude-opus-4-6',
                    max_tokens=2000,
                    messages=[
                        {
                            'role': 'user',
                            'content': improvement_prompt
                        }
                    ]
                )

                improved_definition = response.content[0].text
                new_version = self._increment_version(old_version)

                # Write improved version
                if not self._write_improved_skill(skill_name, improved_definition, new_version):
                    return False, {'error': 'Failed to write improved skill'}

                # Hot-reload
                self.skill_registry.unregister(skill_name)
                reloaded = self.skill_loader.load_skill(skill_name)
                if not reloaded:
                    self.logger.warning(f"[IMPROVE] Failed to reload {skill_name}, reverting...")
                    self._restore_skill(skill_name, backup_path)
                    return False, {'error': 'Failed to reload improved skill'}

                self.logger.info(f"[IMPROVE] Success: {skill_name} v{old_version} → v{new_version}")

                # Send notification
                if self.notification_tool and self.notification_tool.is_configured():
                    self.notification_tool.send_alert(
                        title='Emy: Skill Improved',
                        message=f'{skill_name} v{old_version} → v{new_version}\n'
                                f'Success rate: {old_success_rate:.0%} → target 85%'
                    )

                return True, {
                    'skill': skill_name,
                    'old_version': old_version,
                    'new_version': new_version,
                    'old_success_rate': old_success_rate,
                    'backup_path': str(backup_path)
                }

            except Exception as e:
                self.logger.error(f"[IMPROVE] Error generating improvement: {e}")
                self._restore_skill(skill_name, backup_path)
                return False, {'error': str(e)}

        except Exception as e:
            self.logger.error(f"[IMPROVE] Error improving skill: {e}")
            return False, {'error': str(e)}

    def test_improved_skill(self, skill_name: str, test_runs: int = 3) -> Tuple[bool, float]:
        """
        Test improved skill over N runs.

        Returns:
            (should_keep_improvement, new_success_rate)
        """
        try:
            new_success_rate = self.db.get_skill_success_rate(skill_name, test_runs)

            if new_success_rate >= self.rollback_threshold:
                self.logger.info(
                    f"[IMPROVE] {skill_name} passed testing: {new_success_rate:.1%} >= {self.rollback_threshold:.1%}"
                )
                return True, new_success_rate
            else:
                self.logger.warning(
                    f"[IMPROVE] {skill_name} failed testing: {new_success_rate:.1%} < {self.rollback_threshold:.1%}"
                )
                return False, new_success_rate

        except Exception as e:
            self.logger.error(f"[IMPROVE] Error testing skill: {e}")
            return False, 0.0

    def auto_rollback_skill(self, skill_name: str, backup_path: str) -> bool:
        """Rollback skill to previous version."""
        try:
            return self._restore_skill(skill_name, backup_path)
        except Exception as e:
            self.logger.error(f"[IMPROVE] Error rolling back skill: {e}")
            return False

    def _build_improvement_prompt(self, skill_name: str, current_skill: Dict[str, Any],
                                 success_rate: float) -> str:
        """Build prompt for skill improvement."""
        return f"""You are improving an Emy skill that is underperforming.

Current Skill: {skill_name}
Current Success Rate: {success_rate:.0%}
Target Success Rate: 85%

Current Definition:
{self._skill_dict_to_markdown(current_skill)}

Based on the current definition, provide an IMPROVED version that will increase success rate.
Focus on:
1. Clearer step-by-step instructions
2. Better error handling guidance
3. More specific input/output formats
4. Enhanced self-improvement hooks

Return ONLY the improved markdown (no explanation), with updated version number in frontmatter."""

    def _skill_dict_to_markdown(self, skill: Dict[str, Any]) -> str:
        """Convert skill dict to markdown format."""
        # This is a simplified version; in production would reconstruct full markdown
        lines = ['---']
        for key, value in skill.items():
            if key not in ['content', 'sections']:
                lines.append(f'{key}: {value}')
        lines.append('---')
        if 'content' in skill:
            lines.append(skill['content'])
        return '\n'.join(lines)

    def _backup_skill(self, skill_name: str, version: str) -> Optional[Path]:
        """Backup current skill file."""
        try:
            skill_file = Path(f'emy/skills/definitions/{skill_name}.md')
            if not skill_file.exists():
                return None

            backup_file = Path(f'emy/skills/backups/{skill_name}_v{version}_backup.md')
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            backup_file.write_text(skill_file.read_text())
            self.logger.debug(f"[IMPROVE] Backed up {skill_name} to {backup_file}")
            return backup_file

        except Exception as e:
            self.logger.error(f"[IMPROVE] Error backing up skill: {e}")
            return None

    def _restore_skill(self, skill_name: str, backup_path: Path) -> bool:
        """Restore skill from backup."""
        try:
            if not backup_path.exists():
                self.logger.error(f"[IMPROVE] Backup not found: {backup_path}")
                return False

            skill_file = Path(f'emy/skills/definitions/{skill_name}.md')
            skill_file.write_text(backup_path.read_text())
            self.logger.info(f"[IMPROVE] Restored {skill_name} from {backup_path}")

            # Reload
            self.skill_registry.unregister(skill_name)
            self.skill_loader.load_skill(skill_name)
            return True

        except Exception as e:
            self.logger.error(f"[IMPROVE] Error restoring skill: {e}")
            return False

    def _write_improved_skill(self, skill_name: str, improved_markdown: str, new_version: str) -> bool:
        """Write improved skill definition to file."""
        try:
            skill_file = Path(f'emy/skills/definitions/{skill_name}.md')

            # Update version in frontmatter
            updated = re.sub(
                r'(version:\s*)[\d.]+',
                f'\\g<1>{new_version}',
                improved_markdown
            )

            skill_file.write_text(updated)
            self.logger.debug(f"[IMPROVE] Wrote improved {skill_name} v{new_version}")
            return True

        except Exception as e:
            self.logger.error(f"[IMPROVE] Error writing improved skill: {e}")
            return False

    def _increment_version(self, current_version: str) -> str:
        """Increment version number (1.0 -> 1.1 -> 1.2 -> 2.0)."""
        try:
            parts = current_version.split('.')
            minor = int(parts[-1]) + 1

            if minor >= 10:
                major = int(parts[0]) + 1
                return f'{major}.0'
            else:
                return f'{parts[0]}.{minor}'
        except:
            return '1.1'
