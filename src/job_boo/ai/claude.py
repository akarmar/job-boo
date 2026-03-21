"""Claude AI provider implementation."""

from __future__ import annotations

import json

import anthropic

from job_boo.ai.prompts import (
    COVER_LETTER_PROMPT,
    SCORE_MATCH_PROMPT,
    SKILL_EXTRACTION_PROMPT,
    TAILOR_RESUME_PROMPT,
)
from job_boo.models import Job, MatchResult, Resume


class ClaudeProvider:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _ask(self, system: str, user: str, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def extract_skills(self, resume_text: str) -> Resume:
        raw = self._ask(SKILL_EXTRACTION_PROMPT, resume_text)
        data = json.loads(_extract_json(raw))
        return Resume(
            raw_text=resume_text,
            skills=data.get("skills", []),
            experience_years=data.get("experience_years", 0),
            job_titles=data.get("job_titles", []),
            education=data.get("education", []),
            summary=data.get("summary", ""),
        )

    def score_match(self, resume: Resume, job: Job) -> MatchResult:
        user_msg = f"RESUME SKILLS: {json.dumps(resume.skills)}\n\nRESUME SUMMARY: {resume.summary}\n\nJOB TITLE: {job.title}\nCOMPANY: {job.company}\nJOB DESCRIPTION:\n{job.description[:4000]}"
        raw = self._ask(SCORE_MATCH_PROMPT, user_msg)
        data = json.loads(_extract_json(raw))
        return MatchResult(
            job=job,
            keyword_score=0,  # filled by keyword pass
            ai_score=data.get("score", 0),
            final_score=data.get("score", 0),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            reasoning=data.get("reasoning", ""),
        )

    def tailor_resume(self, resume: Resume, job: Job, match: MatchResult) -> str:
        user_msg = (
            f"ORIGINAL RESUME:\n{resume.raw_text}\n\n"
            f"JOB TITLE: {job.title}\nCOMPANY: {job.company}\n"
            f"JOB DESCRIPTION:\n{job.description[:4000]}\n\n"
            f"MATCHED SKILLS: {json.dumps(match.matched_skills)}\n"
            f"MISSING SKILLS: {json.dumps(match.missing_skills)}"
        )
        return self._ask(TAILOR_RESUME_PROMPT, user_msg, max_tokens=8192)

    def generate_cover_letter(self, resume: Resume, job: Job, match: MatchResult) -> str:
        user_msg = (
            f"RESUME SUMMARY: {resume.summary}\n"
            f"KEY SKILLS: {json.dumps(resume.skills[:15])}\n\n"
            f"JOB TITLE: {job.title}\nCOMPANY: {job.company}\n"
            f"JOB DESCRIPTION:\n{job.description[:3000]}\n\n"
            f"WHY I'M A GOOD FIT: {match.reasoning}"
        )
        return self._ask(COVER_LETTER_PROMPT, user_msg, max_tokens=2048)


def _extract_json(text: str) -> str:
    """Extract JSON from a response that may contain markdown fences."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return text.strip()
