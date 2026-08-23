"""LLM provider factory.

Keeps every LangChain chain/node decoupled from a specific model provider.
Set LLM_PROVIDER in the environment to switch backends without touching any
chain code:

    LLM_PROVIDER=ollama     (default, fully local, no API key needed)
    LLM_PROVIDER=anthropic
    LLM_PROVIDER=groq

If a provider's SDK isn't installed, or an API key is missing, the caller
falls back to a small deterministic stub so the demo keeps working offline
(see app/ai/chains/*.py for the fallback logic around structured output).
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


class LLMUnavailableError(RuntimeError):
    """Raised when no usable chat model backend could be constructed."""


@lru_cache(maxsize=4)
def get_chat_model(temperature: float | None = None):
    """Return a LangChain chat model for the configured provider.

    Cached per (provider, model, temperature) tuple via lru_cache on this
    module-level function's arguments -- since provider/model come from
    settings, effectively one instance per process per temperature value.
    """
    temp = settings.llm_temperature if temperature is None else temperature
    provider = (settings.llm_provider or "ollama").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        model = settings.llm_model or settings.ollama_model
        return ChatOllama(base_url=settings.ollama_base_url, model=model, temperature=temp)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMUnavailableError("ANTHROPIC_API_KEY is not set")
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.llm_model or "claude-3-5-haiku-latest",
            temperature=temp,
        )

    if provider == "groq":
        if not settings.groq_api_key:
            raise LLMUnavailableError("GROQ_API_KEY is not set")
        from langchain_groq import ChatGroq

        return ChatGroq(api_key=settings.groq_api_key, model=settings.llm_model or "llama-3.1-8b-instant", temperature=temp)

    raise LLMUnavailableError(f"Unknown LLM_PROVIDER: {provider!r}")
