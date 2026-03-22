"""USAJobs — US federal government job listings (free, official API)."""

from __future__ import annotations

import re

import httpx

from job_boo.config import Config
from job_boo.models import Job

USAJOBS_URL = "https://data.usajobs.gov/api/Search"


def search_usajobs(config: Config) -> list[Job]:
    """Search USAJobs federal jobs API."""
    api_key = config.sources.usajobs.resolve_key()
    if not api_key:
        raise RuntimeError("USAJobs API key not configured")

    query = config.job_title
    if config.keywords:
        query += " " + " ".join(config.keywords)

    params: dict[str, str | int] = {
        "Keyword": query,
        "ResultsPerPage": 50,
    }

    if config.location.city:
        params["LocationName"] = config.location.city

    headers = {
        "Authorization-Key": api_key,
        "User-Agent": config.sources.usajobs.email or "job-boo-user@example.com",
        "Host": "data.usajobs.gov",
    }

    resp = httpx.get(USAJOBS_URL, params=params, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"USAJobs API returned HTTP {resp.status_code}")
    data = resp.json()

    jobs: list[Job] = []
    items = data.get("SearchResult", {}).get("SearchResultItems", [])
    for item in items:
        desc = item.get("MatchedObjectDescriptor", {})

        # Extract salary
        salary_min = 0
        salary_max = 0
        remuneration = desc.get("PositionRemuneration", [])
        if remuneration:
            pay = remuneration[0]
            try:
                salary_min = int(float(pay.get("MinimumRange", "0")))
                salary_max = int(float(pay.get("MaximumRange", "0")))
            except (ValueError, TypeError):
                pass

        # Extract location
        locations = desc.get("PositionLocation", [])
        location_parts: list[str] = []
        is_remote = False
        for loc in locations[:3]:  # Cap at 3 locations
            name = loc.get("LocationName", "")
            if name:
                location_parts.append(name)
            if "remote" in name.lower() or "telework" in name.lower():
                is_remote = True
        location_str = "; ".join(location_parts)

        # Build description from qualifications + summary
        summary = (
            desc.get("UserArea", {}).get("Details", {}).get("MajorDuties", "") or ""
        )
        qualifications = desc.get("QualificationSummary", "") or ""
        description = f"{summary}\n\n{qualifications}".strip()
        # Strip HTML
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        jobs.append(
            Job(
                title=desc.get("PositionTitle", ""),
                company=desc.get("OrganizationName", ""),
                location=location_str,
                description=description,
                url=desc.get("PositionURI", ""),
                source="usajobs",
                remote=is_remote,
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=desc.get("PublicationStartDate", ""),
                job_id=desc.get("PositionID", ""),
                raw_data=item,
            )
        )

    return jobs
