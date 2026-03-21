"""AI provider abstraction."""

from __future__ import annotations

from rich.console import Console

from job_boo.ai.base import AIProvider
from job_boo.ai.claude import ClaudeProvider
from job_boo.ai.fallback import FallbackProvider
from job_boo.ai.openai_provider import OpenAIProvider
from job_boo.config import AIConfig

console = Console()


def get_provider(config: AIConfig) -> AIProvider:
    """Get the configured AI provider, falling back to keyword-only mode."""
    key = config.resolve_key()
    model = config.resolve_model()
    if not key:
        console.print(
            "[yellow]No AI API key configured. Running in fallback mode "
            "(keyword-only matching, no tailoring).[/yellow]\n"
            "[dim]Run 'job-boo setup-ai' to enable AI-powered features.[/dim]\n"
        )
        return FallbackProvider()  # type: ignore[return-value]
    if config.provider == "openai":
        return OpenAIProvider(api_key=key, model=model)
    return ClaudeProvider(api_key=key, model=model)
