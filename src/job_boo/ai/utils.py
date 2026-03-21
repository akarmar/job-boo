"""Shared utilities for AI providers."""

from __future__ import annotations

import re


def extract_json(text: str) -> str:
    """Extract the first JSON block from LLM output."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()
