"""Test the approval flow with a fake model: the DB is written only after approval, not on rejection."""
import sqlite3

from conftest import ScriptedModel, call
from langchain_core.messages import AIMessage

from bankbot.agent import ask, build_agent, tools_called


def disputes(db):
    return sqlite3.connect(db).execute("SELECT COUNT(*) FROM disputes").fetchone()[0]


def script():
    return ScriptedModel(responses=[
        call("create_dispute_ticket", {"txn_id": "T9002", "reason": "duplicate charge"}),
        AIMessage(content="Done."),
    ])


def test_dispute_runs_only_after_approval(db, store):
    agent = build_agent("C001", llm=script(), store=store, db_path=db)
    result = ask(agent, "dispute T9002", "t1")  # no decide passed: stops at approval
    assert result["__interrupt__"]
    assert disputes(db) == 0  # not approved yet, nothing in the DB
    from langgraph.types import Command
    agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}),
                 {"configurable": {"thread_id": "t1"}})
    assert disputes(db) == 1


def test_rejected_dispute_writes_nothing(db, store):
    agent = build_agent("C001", llm=script(), store=store, db_path=db)
    result = ask(agent, "dispute T9002", "t2", decide=lambda r: {"type": "reject", "message": "no"})
    assert disputes(db) == 0
    assert tools_called(result) == ["create_dispute_ticket"]


def test_read_tools_do_not_need_approval(db, store):
    llm = ScriptedModel(responses=[call("list_accounts", {}), AIMessage(content="ok")])
    agent = build_agent("C001", llm=llm, store=store, db_path=db)
    result = ask(agent, "balances?", "t3")
    assert not result.get("__interrupt__")
