"""Modul integrasi LLM."""

try:
    from src.llm.openai_client import OpenAIClient
    from src.llm.prompt_loader import PromptLoader
except ModuleNotFoundError:
    from backend.src.llm.openai_client import OpenAIClient
    from backend.src.llm.prompt_loader import PromptLoader

__all__ = ["OpenAIClient", "PromptLoader"]
