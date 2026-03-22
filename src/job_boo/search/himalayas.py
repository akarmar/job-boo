"""Himalayas — curated remote jobs with salary data (free, no API key)."""

from __future__ import annotations

import re

import httpx

from job_boo.config import Config
from job_boo.models import Job

HIMALAYAS_URL = "https://himalayas.app/jobs/api/search"


def search_himalayas(config: Config) -> list[Job]:
    """Search Himalayas remote jobs API."""
    query = config.job_title
    if config.keywords:
        query += " " + " ".join(config.keywords)

    params: dict[str, str | int] = {
        "q": query,
        "page": 1,
    }

    resp = httpx.get(HIMALAYAS_URL, params=params, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Himalayas API returned HTTP {resp.status_code}")
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type and "text/json" not in content_type:
        raise RuntimeError(
            f"Himalayas returned unexpected content-type: {content_type}"
        )
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        description = item.get("description", "") or ""
        # Strip HTML
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        salary_min = item.get("minSalary") or 0
        salary_max = item.get("maxSalary") or 0

        # Location from restrictions or "Remote"
        location_restrictions = item.get("locationRestrictions") or []
        location_str = (
            ", ".join(location_restrictions) if location_restrictions else "Remote"
        )

        jobs.append(
            Job(
                title=item.get("title", ""),
                company=item.get("companyName", ""),
                location=location_str,
                description=description,
                url=f"https://himalayas.app/jobs/{item.get('slug', '')}",
                source="himalayas",
                remote=True,  # Himalayas is remote-only
                salary_min=int(salary_min) if salary_min else 0,
                salary_max=int(salary_max) if salary_max else 0,
                posted_date=item.get("pubDate", ""),
                job_id=str(item.get("id", "")),
                raw_data=item,
            )
        )

    return jobs
