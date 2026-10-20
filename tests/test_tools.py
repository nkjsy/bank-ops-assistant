import json

from bankbot.tools import build_tools


def tool_map(db, customer, store=None):
    return {t.name: t for t in build_tools(customer, db_path=db, store=store)}


def test_customer_only_sees_own_accounts(db):
    t = tool_map(db, "C001")
    accounts = json.loads(t["list_accounts"].invoke({}))
    assert {a["account_id"] for a in accounts} == {"A001", "A002"}


def test_cannot_read_other_customers_account(db):
    t = tool_map(db, "C001")
    out = t["list_transactions"].invoke({"account_id": "A003"})  # A003 属于 C002
    assert out.startswith("Error")
    assert "BlueBottle" not in out


def test_spending_summary_matches_known_numbers(db):
    t = tool_map(db, "C001")
    rows = json.loads(t["spending_summary"].invoke(
        {"account_id": "A001", "start_date": "2026-09-01", "end_date": "2026-09-30"}))
    by_cat = {r["category"]: r["spent"] for r in rows}
    assert by_cat["fees"] == 4.5 and by_cat["shopping"] == 150.0


def test_dispute_rejects_foreign_transaction(db):
    t = tool_map(db, "C001")
    assert t["create_dispute_ticket"].invoke({"txn_id": "T9101", "reason": "x"}).startswith("Error")


def test_search_policy_finds_right_source(store):
    t = {x.name: x for x in build_tools("C001", store=store)}
    out = t["search_policy"].invoke({"query": "international transaction fee percentage"})
    assert "fees.md" in out and "3%" in out
