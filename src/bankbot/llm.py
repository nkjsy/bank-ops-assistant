"""Create the model from environment variables. To switch models, only change LLM_MODEL in .env; no code changes."""
from langchain.chat_models import init_chat_model

from . import config


def get_llm(model: str | None = None):
    return init_chat_model(model or config.LLM_MODEL, temperature=0)
