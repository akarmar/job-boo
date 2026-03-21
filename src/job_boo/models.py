"""Core data models for job-boo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobState(str, Enum):
    FOUND = "found"
    SCORED = "scored"
    TAILORED = "tailored"
    READY = "ready"
    APPLIED = "applied"
    FOLLOWED_UP = "followed_up"
    CLOSED = "closed"
    SKIPPED = "skipped"


class LocationPref(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


@dataclass
class Resume:
    raw_text: str
    skills: list[str] = field(default_factory=list)
    experience_years: int = 0
    job_titles: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    summary: str = ""
    source_path: str = ""


@dataclass
class Job:
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str  # which API/source found it
    salary_min: int = 0
    salary_max: int = 0
    remote: bool = False
    sponsorship_available: bool | None = None  # None = unknown
    posted_date: str = ""
    job_id: str = ""  # internal ID from source
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.description) > 5000:
            self.description = self.description[:5000]

    def dedup_key(self) -> str:
        """Key for deduplication across sources."""
        return f"{self.company.lower().strip()}|{self.title.lower().strip()}"


@dataclass
class MatchResult:
    job: Job
    keyword_score: float  # 0-100, from keyword overlap
    ai_score: float  # 0-100, from AI semantic analysis
    final_score: float  # 0-100, weighted combination
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    reasoning: str = ""
    location_fit: bool = True
    sponsorship_fit: bool = True


@dataclass
class Application:
    job: Job
    match: MatchResult
    state: JobState = JobState.FOUND
    tailored_resume_path: str = ""
    cover_letter_path: str = ""
    applied_at: datetime | None = None
    notes: str = ""
    db_id: int | None = None
