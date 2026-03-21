"""AI provider abstraction."""

from job_boo.ai.base import AIProvider
from job_boo.ai.claude import ClaudeProvider
from job_boo.ai.openai_provider import OpenAIProvider
from job_boo.config import AIConfig


def get_provider(config: AIConfig) -> AIProvider:
    key = config.resolve_key()
    model = config.resolve_model()
    if not key:
        raise ValueError(
            f"No API key found for {config.provider}. "
            "Set it in config.yaml or JOB_BOO_AI_KEY env var."
        )
    if config.provider == "openai":
        return OpenAIProvider(api_key=key, model=model)
    return ClaudeProvider(api_key=key, model=model)
