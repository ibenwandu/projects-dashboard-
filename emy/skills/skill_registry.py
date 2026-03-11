"""
Skill registry - in-memory index of all available skills.

Maintains loaded skill definitions and enables fast lookups.
Hot-reloadable for skill self-improvement.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger('SkillRegistry')


class EMySkillRegistry:
    """In-memory registry of skills."""

    def __init__(self):
        """Initialize skill registry."""
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger('SkillRegistry')

    def register(self, skill_name: str, skill_def: Dict[str, Any]) -> bool:
        """
        Register a skill definition.

        Args:
            skill_name: Unique skill name
            skill_def: Skill definition dict (from loader)

        Returns:
            True if registered, False if error
        """
        try:
            if 'name' not in skill_def:
                skill_def['name'] = skill_name

            self.skills[skill_name] = skill_def
            self.logger.info(f"[REGISTER] {skill_name} v{skill_def.get('version', '?')}")
            return True
        except Exception as e:
            self.logger.error(f"Error registering skill {skill_name}: {e}")
            return False

    def get(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get a registered skill by name."""
        return self.skills.get(skill_name)

    def list_all(self) -> List[str]:
        """List all registered skill names."""
        return sorted(self.skills.keys())

    def list_by_domain(self, domain: str) -> List[str]:
        """List skills in a specific domain."""
        return [name for name, skill in self.skills.items()
                if skill.get('domain') == domain]

    def unregister(self, skill_name: str) -> bool:
        """Unregister a skill (for hot-reload)."""
        if skill_name in self.skills:
            del self.skills[skill_name]
            self.logger.info(f"[UNREGISTER] {skill_name}")
            return True
        return False

    def clear(self):
        """Clear all registered skills."""
        self.skills.clear()
        self.logger.info("[CLEAR] All skills unregistered")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        domains = {}
        for skill_def in self.skills.values():
            domain = skill_def.get('domain', 'unknown')
            domains[domain] = domains.get(domain, 0) + 1

        return {
            'total_skills': len(self.skills),
            'by_domain': domains,
            'skills': self.list_all()
        }
