"""
LLM Factory — returns a configured BaseChatModel instance.

Provider is selected via the LLM_PROVIDER environment variable.
Supported values: "gemini" (default), "openai", "anthropic".

Environment variables required per provider:
  - gemini:    GEMINI_API_KEY
  - openai:    OPENAI_API_KEY
  - anthropic: ANTHROPIC_API_KEY

Usage:
    from app.agents.llm_factory import get_llm
    llm = get_llm()
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns a configured LLM instance based on the LLM_PROVIDER env var.

    Args:
        temperature: Sampling temperature (0.0 = deterministic).

    Returns:
        A LangChain-compatible BaseChatModel instance.

    Raises:
        ValueError: If an unsupported provider is configured.
        ImportError: If the required langchain integration package is missing.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()

    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise ImportError(
                "langchain-google-genai is required for the Gemini provider. "
                "Install it with: uv add langchain-google-genai"
            ) from e

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            temperature=temperature,
            google_api_key=api_key,
        )

    elif provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise ImportError(
                "langchain-openai is required for the OpenAI provider. "
                "Install it with: uv add langchain-openai"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=temperature,
            api_key=api_key,
        )

    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise ImportError(
                "langchain-anthropic is required for the Anthropic provider. "
                "Install it with: uv add langchain-anthropic"
            ) from e

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            temperature=temperature,
            api_key=api_key,
        )

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            "Valid options are: 'gemini', 'openai', 'anthropic'."
        )
