"""AI provider protocol."""

from __future__ import annotations

from typing import Protocol

from job_boo.models import Job, Resume, MatchResult


class AIProvider(Protocol):
    def extract_skills(self, resume_text: str) -> Resume:
        """Parse resume text and extract structured data."""
        ...

    def score_match(self, resume: Resume, job: Job) -> MatchResult:
        """Score how well a resume matches a job listing."""
        ...

    def tailor_resume(self, resume: Resume, job: Job, match: MatchResult) -> str:
        """Generate a tailored resume text for a specific job."""
        ...

    def generate_cover_letter(self, resume: Resume, job: Job, match: MatchResult) -> str:
        """Generate a cover letter for a specific job."""
        ...
