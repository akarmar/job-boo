"""The Muse job search API (free, no key needed)."""

from __future__ import annotations

import re

import httpx

from job_boo.config import Config
from job_boo.models import Job

MUSE_CATEGORIES = {
    "software engineer": "Engineering",
    "data scientist": "Data Science",
    "product manager": "Product",
    "designer": "Design",
    "marketing": "Marketing",
    "sales": "Sales",
    "finance": "Finance",
    "operations": "Operations",
}


def search_themuse(config: Config) -> list[Job]:
    """Search The Muse API."""
    params: dict[str, str | int] = {
        "page": 0,
        "descending": "true",
    }

    # Map job title to Muse category
    title_lower = config.job_title.lower()
    for keyword, category in MUSE_CATEGORIES.items():
        if keyword in title_lower:
            params["category"] = category
            break

    if config.location.city:
        params["location"] = config.location.city

    resp = httpx.get(
        "https://www.themuse.com/api/public/jobs", params=params, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()

    jobs: list[Job] = []
    for item in data.get("results", []):
        locations = [loc.get("name", "") for loc in item.get("locations", [])]
        location_str = ", ".join(locations)
        is_remote = any(
            "remote" in loc.lower() or "flexible" in loc.lower() for loc in locations
        )

        contents = item.get("contents", "")
        # Strip HTML tags for plain text description
        description = re.sub(r"<[^>]+>", " ", contents)
        description = re.sub(r"\s+", " ", description).strip()

        jobs.append(
            Job(
                title=item.get("name", ""),
                company=item.get("company", {}).get("name", ""),
                location=location_str,
                description=description,
                url=item.get("refs", {}).get("landing_page", ""),
                source="themuse",
                remote=is_remote,
                posted_date=item.get("publication_date", ""),
                job_id=str(item.get("id", "")),
                raw_data=item,
            )
        )

    return jobs
