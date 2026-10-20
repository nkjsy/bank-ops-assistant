"""按环境变量创建模型。换模型只改 .env 里的 LLM_MODEL，代码不用动。"""
from langchain.chat_models import init_chat_model

from . import config


def get_llm(model: str | None = None):
    return init_chat_model(model or config.LLM_MODEL, temperature=0)
