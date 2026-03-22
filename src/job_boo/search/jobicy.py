"""Jobicy — remote job listings with salary data (free, no API key)."""

from __future__ import annotations

import re

import httpx

from job_boo.config import Config
from job_boo.models import Job

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


def search_jobicy(config: Config) -> list[Job]:
    """Search Jobicy remote jobs API."""
    params: dict[str, str | int] = {
        "count": 50,
        "geo": "usa",
    }

    # Jobicy tag search works best with single keywords — pick the most descriptive word
    # from the job title (e.g., "analyst" from "Data Analyst", "engineer" from "Software Engineer")
    stop_words = {
        "senior",
        "junior",
        "lead",
        "staff",
        "principal",
        "sr",
        "jr",
        "the",
        "a",
        "an",
    }
    title_words = [w for w in config.job_title.lower().split() if w not in stop_words]
    tag = title_words[-1] if title_words else config.job_title.split()[-1]
    params["tag"] = tag

    resp = httpx.get(JOBICY_URL, params=params, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Jobicy API returned HTTP {resp.status_code}")
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type and "text/json" not in content_type:
        raise RuntimeError(f"Jobicy returned unexpected content-type: {content_type}")
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        description = item.get("jobDescription", "") or ""
        # Strip HTML
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        salary_min = item.get("annualSalaryMin") or 0
        salary_max = item.get("annualSalaryMax") or 0

        location_str = item.get("jobGeo", "") or "Remote"

        jobs.append(
            Job(
                title=item.get("jobTitle", ""),
                company=item.get("companyName", ""),
                location=location_str,
                description=description,
                url=item.get("url", ""),
                source="jobicy",
                remote=True,  # Jobicy is remote-only
                salary_min=int(salary_min) if salary_min else 0,
                salary_max=int(salary_max) if salary_max else 0,
                posted_date=item.get("pubDate", ""),
                job_id=str(item.get("id", "")),
                raw_data=item,
            )
        )

    return jobs
