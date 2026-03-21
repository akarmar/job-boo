"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import yaml


CONFIG_DIR = Path.home() / ".job-boo"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
DB_PATH = CONFIG_DIR / "jobs.db"
OUTPUT_DIR = CONFIG_DIR / "output"


@dataclass
class AIConfig:
    provider: str = "claude"
    api_key: str = ""
    model: str = ""

    def resolve_key(self) -> str:
        if self.api_key:
            return self.api_key
        return os.environ.get("JOB_BOO_AI_KEY", "")

    def resolve_model(self) -> str:
        if self.model:
            return self.model
        if self.provider == "claude":
            return "claude-sonnet-4-20250514"
        return "gpt-4o"


@dataclass
class SerpApiConfig:
    enabled: bool = False
    api_key: str = ""

    def resolve_key(self) -> str:
        return self.api_key or os.environ.get("SERPAPI_KEY", "")


@dataclass
class AdzunaConfig:
    enabled: bool = True
    app_id: str = ""
    api_key: str = ""
    country: str = "us"

    def resolve_app_id(self) -> str:
        return self.app_id or os.environ.get("ADZUNA_APP_ID", "")

    def resolve_key(self) -> str:
        return self.api_key or os.environ.get("ADZUNA_API_KEY", "")


@dataclass
class JobSpyConfig:
    enabled: bool = False
    sites: list[str] = field(
        default_factory=lambda: ["indeed", "linkedin", "glassdoor"]
    )
    proxy: str = ""  # optional proxy URL
    results_per_site: int = 25


@dataclass
class SourcesConfig:
    serpapi: SerpApiConfig = field(default_factory=SerpApiConfig)
    adzuna: AdzunaConfig = field(default_factory=AdzunaConfig)
    jobspy: JobSpyConfig = field(default_factory=JobSpyConfig)
    themuse: bool = True
    remotive: bool = True


@dataclass
class SalaryConfig:
    min: int = 0
    max: int = 0
    currency: str = "USD"


@dataclass
class LocationConfig:
    preference: str = "remote"
    city: str = ""


@dataclass
class ApplyConfig:
    confirm_before_submit: bool = True
    include_cover_letter: bool = True
    delay_between_applications: int = 5


@dataclass
class CompaniesConfig:
    blacklist: list[str] = field(default_factory=list)
    whitelist: list[str] = field(default_factory=list)


@dataclass
class Config:
    resume_path: str = ""
    job_title: str = ""
    keywords: list[str] = field(default_factory=list)
    location: LocationConfig = field(default_factory=LocationConfig)
    needs_sponsorship: bool = False
    salary: SalaryConfig = field(default_factory=SalaryConfig)
    match_threshold: int = 60
    ai: AIConfig = field(default_factory=AIConfig)
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    output_dir: str = str(OUTPUT_DIR)
    apply: ApplyConfig = field(default_factory=ApplyConfig)
    companies: CompaniesConfig = field(default_factory=CompaniesConfig)
    profiles: dict[str, dict] = field(default_factory=dict)


def _get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def load_config(path: Path | None = None) -> Config:
    """Load config from YAML file, with env var fallbacks."""
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        return Config()

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    sources_data = data.get("sources", {})
    serpapi_data = sources_data.get("serpapi", {})
    adzuna_data = sources_data.get("adzuna", {})
    jobspy_data = sources_data.get("jobspy", {})
    loc_data = data.get("location", {})
    salary_data = data.get("salary", {})
    ai_data = data.get("ai", {})
    apply_data = data.get("apply", {})
    companies_data = data.get("companies", {})
    profiles_data = data.get("profiles", {})

    return Config(
        resume_path=data.get("resume_path", ""),
        job_title=data.get("job_title", ""),
        keywords=data.get("keywords", []),
        location=LocationConfig(
            preference=loc_data.get("preference", "remote"),
            city=loc_data.get("city", ""),
        ),
        needs_sponsorship=data.get("needs_sponsorship", False),
        salary=SalaryConfig(
            min=salary_data.get("min", 0),
            max=salary_data.get("max", 0),
            currency=salary_data.get("currency", "USD"),
        ),
        match_threshold=data.get("match_threshold", 60),
        ai=AIConfig(
            provider=ai_data.get("provider", "claude"),
            api_key=ai_data.get("api_key", ""),
            model=ai_data.get("model", ""),
        ),
        sources=SourcesConfig(
            serpapi=SerpApiConfig(
                enabled=serpapi_data.get("enabled", False),
                api_key=serpapi_data.get("api_key", ""),
            ),
            adzuna=AdzunaConfig(
                enabled=adzuna_data.get("enabled", True),
                app_id=adzuna_data.get("app_id", ""),
                api_key=adzuna_data.get("api_key", ""),
                country=adzuna_data.get("country", "us"),
            ),
            jobspy=JobSpyConfig(
                enabled=jobspy_data.get("enabled", False),
                sites=jobspy_data.get("sites", ["indeed", "linkedin", "glassdoor"]),
                proxy=jobspy_data.get("proxy", ""),
                results_per_site=jobspy_data.get("results_per_site", 25),
            ),
            themuse=sources_data.get("themuse", {}).get("enabled", True)
            if isinstance(sources_data.get("themuse"), dict)
            else sources_data.get("themuse", True),
            remotive=sources_data.get("remotive", {}).get("enabled", True)
            if isinstance(sources_data.get("remotive"), dict)
            else sources_data.get("remotive", True),
        ),
        output_dir=data.get("output_dir", str(OUTPUT_DIR)),
        apply=ApplyConfig(
            confirm_before_submit=apply_data.get("confirm_before_submit", True),
            include_cover_letter=apply_data.get("include_cover_letter", True),
            delay_between_applications=apply_data.get("delay_between_applications", 5),
        ),
        companies=CompaniesConfig(
            blacklist=companies_data.get("blacklist", []),
            whitelist=companies_data.get("whitelist", []),
        ),
        profiles=profiles_data if isinstance(profiles_data, dict) else {},
    )


def apply_profile(config: Config, profile_name: str) -> Config:
    """Merge a named profile's settings into the config, overriding job_title, keywords, and resume_path."""
    if profile_name not in config.profiles:
        raise click.ClickException(
            f"Profile '{profile_name}' not found. "
            f"Available profiles: {', '.join(config.profiles.keys()) or '(none)'}"
        )
    profile = config.profiles[profile_name]
    if "job_title" in profile:
        config.job_title = profile["job_title"]
    if "keywords" in profile:
        config.keywords = profile["keywords"]
    if "resume_path" in profile:
        config.resume_path = profile["resume_path"]
    return config


def ensure_dirs(config: Config) -> None:
    """Create necessary directories."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(
        CONFIG_DIR, 0o700
    )  # nosemgrep: insecure-file-permissions — owner-only dir for secrets
    Path(config.output_dir).expanduser().mkdir(parents=True, exist_ok=True)
