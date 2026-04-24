"""
Central model/configuration helpers.

The project uses OpenAI models through ADK's LiteLLM wrapper, so every
agent can share one ``build_model()`` factory. Swap to Gemini by
replacing the body of ``build_model`` with a plain string model name.
"""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm


DEFAULT_MODEL = "gpt-4o-mini"


def build_model() -> LiteLlm:
    """Return a LiteLlm model bound to OpenAI using env config.

    Reads ``OPENAI_MODEL`` from the environment and wraps it so ADK can
    route calls via LiteLLM. ``OPENAI_API_KEY`` must also be set; LiteLLM
    picks it up automatically.
    """
    model_name = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return LiteLlm(model=f"openai/{model_name}")
