"""
Database module adapter - provides Trade-Alerts compatible database access.

For Emy, we use the main EMyDatabase from core.
For backward compatibility with Trade-Alerts modules, this provides access.
"""

from emy.core.database import EMyDatabase

# Singleton instance
_db_instance = None

def get_database(db_path: str = "emy/data/emy.db") -> EMyDatabase:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EMyDatabase(db_path)
        _db_instance.initialize_schema()
    return _db_instance
