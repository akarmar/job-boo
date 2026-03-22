"""The Muse job search API (free, no key needed)."""

from __future__ import annotations

import re

import httpx

from job_boo.config import Config
from job_boo.models import Job

_CAT_ENGINEERING = "Engineering"
_CAT_DATA_SCIENCE = "Data Science"
_CAT_DESIGN = "Design"
_CAT_FINANCE = "Finance"
_CAT_HR = "HR"

MUSE_CATEGORIES = {
    "software engineer": _CAT_ENGINEERING,
    "software developer": _CAT_ENGINEERING,
    "backend engineer": _CAT_ENGINEERING,
    "frontend engineer": _CAT_ENGINEERING,
    "full stack": _CAT_ENGINEERING,
    "devops": _CAT_ENGINEERING,
    "sre": _CAT_ENGINEERING,
    "data scientist": _CAT_DATA_SCIENCE,
    "data analyst": _CAT_DATA_SCIENCE,
    "data engineer": _CAT_DATA_SCIENCE,
    "business analyst": _CAT_DATA_SCIENCE,
    "machine learning": _CAT_DATA_SCIENCE,
    "analyst": _CAT_DATA_SCIENCE,
    "product manager": "Product",
    "project manager": "Project Management",
    "designer": _CAT_DESIGN,
    "ux": _CAT_DESIGN,
    "ui": _CAT_DESIGN,
    "marketing": "Marketing",
    "sales": "Sales",
    "finance": _CAT_FINANCE,
    "accounting": _CAT_FINANCE,
    "operations": "Operations",
    "hr": _CAT_HR,
    "human resources": _CAT_HR,
}


def _resolve_muse_category(config: Config) -> str | None:
    """Map job title or keywords to a Muse API category."""
    search_terms = [config.job_title.lower()]
    search_terms.extend(kw.lower() for kw in config.keywords)

    for term in search_terms:
        for keyword, category in MUSE_CATEGORIES.items():
            if keyword in term:
                return category
    return None


def search_themuse(config: Config) -> list[Job]:
    """Search The Muse API."""
    params: dict[str, str | int] = {
        "page": 0,
        "descending": "true",
    }

    category = _resolve_muse_category(config)
    if category:
        params["category"] = category

    if config.location.city:
        params["location"] = config.location.city

    resp = httpx.get(
        "https://www.themuse.com/api/public/jobs", params=params, timeout=30
    )
    if resp.status_code != 200:
        raise RuntimeError(f"The Muse API returned HTTP {resp.status_code}")
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type and "text/json" not in content_type:
        raise RuntimeError(f"Source returned unexpected content-type: {content_type}")
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
