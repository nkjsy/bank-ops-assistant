import os

os.environ["EMBEDDINGS"] = "fake"  # don't download the embedding model in tests

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from bankbot import data_gen, rag


class ScriptedModel(BaseChatModel):
    """Fake model: returns pre-written replies in order, used to test the agent flow without an API key."""
    responses: list
    i: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self.responses[self.i]
        self.i += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self):
        return "scripted"


def call(name, args, id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id}])


@pytest.fixture()
def db(tmp_path):
    return data_gen.generate(tmp_path / "bank.db")


@pytest.fixture()
def store(tmp_path):
    return rag.build_index(persist_dir=tmp_path / "chroma")
