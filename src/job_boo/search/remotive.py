"""Remotive API — remote jobs only (free, no key needed)."""

from __future__ import annotations

import httpx

from job_boo.config import Config
from job_boo.models import Job

REMOTIVE_CATEGORIES = {
    "software": "software-dev",
    "engineer": "software-dev",
    "developer": "software-dev",
    "data": "data",
    "devops": "devops-sysadmin",
    "sre": "devops-sysadmin",
    "design": "design",
    "product": "product",
    "marketing": "marketing",
    "customer": "customer-support",
    "qa": "qa",
    "writing": "writing",
}


def search_remotive(config: Config) -> list[Job]:
    """Search Remotive for remote jobs."""
    params: dict[str, str] = {}

    title_lower = config.job_title.lower()
    for keyword, category in REMOTIVE_CATEGORIES.items():
        if keyword in title_lower:
            params["category"] = category
            break

    if config.job_title:
        params["search"] = config.job_title

    resp = httpx.get("https://remotive.com/api/remote-jobs", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        import re

        description = re.sub(r"<[^>]+>", " ", item.get("description", ""))
        description = re.sub(r"\s+", " ", description).strip()

        salary = item.get("salary", "")
        salary_min = 0
        if salary:
            nums = re.findall(r"[\d,]+", salary)
            if nums:
                salary_min = int(nums[0].replace(",", ""))

        jobs.append(
            Job(
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Anywhere"),
                description=description[:5000],
                url=item.get("url", ""),
                source="remotive",
                remote=True,
                salary_min=salary_min,
                posted_date=item.get("publication_date", ""),
                job_id=str(item.get("id", "")),
                raw_data=item,
            )
        )

    return jobs
