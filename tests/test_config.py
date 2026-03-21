"""Tests for configuration loading and validation."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml

from job_boo.config import (
    AIConfig,
    AdzunaConfig,
    Config,
    SerpApiConfig,
    apply_profile,
    ensure_dirs,
    load_config,
)


class TestAIConfig:
    def test_resolve_key_from_field(self) -> None:
        cfg = AIConfig(api_key="my-key")
        assert cfg.resolve_key() == "my-key"

    def test_resolve_key_from_env(self) -> None:
        cfg = AIConfig()
        with patch.dict(os.environ, {"JOB_BOO_AI_KEY": "env-key"}):
            assert cfg.resolve_key() == "env-key"

    def test_resolve_key_empty(self) -> None:
        cfg = AIConfig()
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            os.environ.pop("JOB_BOO_AI_KEY", None)
            assert cfg.resolve_key() == ""

    def test_resolve_key_field_takes_precedence(self) -> None:
        cfg = AIConfig(api_key="field-key")
        with patch.dict(os.environ, {"JOB_BOO_AI_KEY": "env-key"}):
            assert cfg.resolve_key() == "field-key"

    def test_resolve_model_claude_default(self) -> None:
        cfg = AIConfig(provider="claude")
        assert "claude" in cfg.resolve_model()

    def test_resolve_model_openai_default(self) -> None:
        cfg = AIConfig(provider="openai")
        assert cfg.resolve_model() == "gpt-4o"

    def test_resolve_model_explicit(self) -> None:
        cfg = AIConfig(model="custom-model")
        assert cfg.resolve_model() == "custom-model"


class TestSerpApiConfig:
    def test_resolve_key_from_field(self) -> None:
        cfg = SerpApiConfig(api_key="serp-key")
        assert cfg.resolve_key() == "serp-key"

    def test_resolve_key_from_env(self) -> None:
        cfg = SerpApiConfig()
        with patch.dict(os.environ, {"SERPAPI_KEY": "env-serp-key"}):
            assert cfg.resolve_key() == "env-serp-key"


class TestAdzunaConfig:
    def test_resolve_app_id_from_env(self) -> None:
        cfg = AdzunaConfig()
        with patch.dict(os.environ, {"ADZUNA_APP_ID": "env-app-id"}):
            assert cfg.resolve_app_id() == "env-app-id"

    def test_resolve_key_from_env(self) -> None:
        cfg = AdzunaConfig()
        with patch.dict(os.environ, {"ADZUNA_API_KEY": "env-api-key"}):
            assert cfg.resolve_key() == "env-api-key"


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.job_title == ""
        assert config.keywords == []
        assert config.match_threshold == 60

    def test_empty_yaml_file(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        config = load_config(config_path)
        assert config.job_title == ""

    def test_valid_yaml(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {
            "job_title": "Data Engineer",
            "keywords": ["spark", "python"],
            "match_threshold": 75,
            "location": {"preference": "hybrid", "city": "NYC"},
            "salary": {"min": 120000, "max": 180000},
            "ai": {"provider": "openai", "api_key": "test-key"},
            "sources": {
                "adzuna": {"enabled": True, "app_id": "aid", "api_key": "akey"},
                "serpapi": {"enabled": False},
                "themuse": True,
                "remotive": False,
            },
        }
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert config.job_title == "Data Engineer"
        assert config.keywords == ["spark", "python"]
        assert config.match_threshold == 75
        assert config.location.preference == "hybrid"
        assert config.location.city == "NYC"
        assert config.salary.min == 120000
        assert config.ai.provider == "openai"
        assert config.sources.adzuna.enabled is True
        assert config.sources.themuse is True
        assert config.sources.remotive is False

    def test_invalid_yaml_raises_click_exception(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("{{invalid: yaml: [")
        with pytest.raises(click.ClickException, match="Invalid config file"):
            load_config(config_path)

    def test_themuse_as_dict(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {"sources": {"themuse": {"enabled": False}}}
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert config.sources.themuse is False

    def test_profiles_loaded(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {
            "profiles": {
                "sre": {"job_title": "Site Reliability Engineer", "keywords": ["k8s"]},
            }
        }
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert "sre" in config.profiles

    def test_profiles_not_dict_defaults_to_empty(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {"profiles": "not a dict"}
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert config.profiles == {}

    def test_needs_sponsorship(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {"needs_sponsorship": True}
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert config.needs_sponsorship is True

    def test_companies_blacklist(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {"companies": {"blacklist": ["Evil Corp"], "whitelist": ["Good Inc"]}}
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert config.companies.blacklist == ["Evil Corp"]
        assert config.companies.whitelist == ["Good Inc"]

    def test_jobspy_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        data = {
            "sources": {
                "jobspy": {
                    "enabled": True,
                    "sites": ["indeed"],
                    "proxy": "http://proxy:8080",
                    "results_per_site": 10,
                }
            }
        }
        config_path.write_text(yaml.dump(data))
        config = load_config(config_path)
        assert config.sources.jobspy.enabled is True
        assert config.sources.jobspy.sites == ["indeed"]
        assert config.sources.jobspy.proxy == "http://proxy:8080"
        assert config.sources.jobspy.results_per_site == 10


class TestApplyProfile:
    def test_apply_valid_profile(self, config_with_profiles: Config) -> None:
        config = apply_profile(config_with_profiles, "frontend")
        assert config.job_title == "Frontend Developer"
        assert config.keywords == ["react", "typescript"]
        assert config.resume_path == "/tmp/frontend_resume.pdf"

    def test_apply_partial_profile(self, config_with_profiles: Config) -> None:
        config = apply_profile(config_with_profiles, "data")
        assert config.job_title == "Data Engineer"
        assert config.keywords == ["spark", "airflow"]
        # resume_path unchanged
        assert config.resume_path == ""

    def test_missing_profile_raises(self, config_with_profiles: Config) -> None:
        with pytest.raises(click.ClickException, match="Profile 'nonexistent' not found"):
            apply_profile(config_with_profiles, "nonexistent")

    def test_missing_profile_shows_available(self, config_with_profiles: Config) -> None:
        with pytest.raises(click.ClickException, match="frontend"):
            apply_profile(config_with_profiles, "nonexistent")

    def test_no_profiles_available(self) -> None:
        config = Config()
        with pytest.raises(click.ClickException, match="(none)"):
            apply_profile(config, "anything")


class TestEnsureDirs:
    def test_creates_output_dir(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        config = Config(output_dir=str(output_dir))
        with patch("job_boo.config.CONFIG_DIR", tmp_path / "config"):
            ensure_dirs(config)
        assert output_dir.exists()
