"""Core data model for job listings."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobDetails:
    """Unified job representation across all platforms."""

    # Platform and identification
    url: str                    # Platform-specific job URL
    platform: str               # "linkedin", "glassdoor", "indeed"
    job_id: str                 # Platform-specific ID
    fingerprint: str = ""       # Hash for deduplication (computed later)

    # Job information
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""            # "90000-120000" or ""
    job_type: str = ""          # "Full-time", "Contract", "Permanent"
    description: str = ""       # Full job description
    skills: list[str] = field(default_factory=list)

    # AI scoring
    score: int = 0              # 0-100
    reasoning: str = ""         # Why score given

    # Metadata
    fetched_at: str = ""        # ISO timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "platform": self.platform,
            "job_id": self.job_id,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "job_type": self.job_type,
            "description": self.description,
            "skills": self.skills,
            "score": self.score,
            "reasoning": self.reasoning,
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JobDetails:
        """Create from dictionary (for JSON deserialization)."""
        return cls(**data)
