"""Tools the agent can use.

Key design: build_tools(customer_id) locks the "current customer" into every tool.
Even if the model is manipulated, it can only see this customer's own accounts: permissions are enforced by code, not by prompt persuasion.
"""
import json
import sqlite3
import uuid
from datetime import datetime

from langchain_core.tools import tool

from . import config, rag


def build_tools(customer_id: str, db_path=None, store=None):
    db_path = db_path or config.DB_PATH

    def conn():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c

    def own_account(c, account_id: str) -> bool:
        row = c.execute("SELECT 1 FROM accounts WHERE account_id=? AND customer_id=?",
                        (account_id, customer_id)).fetchone()
        return row is not None

    @tool
    def list_accounts() -> str:
        """List the current customer's accounts with account_id, type and current balance."""
        with conn() as c:
            rows = c.execute("SELECT account_id, type, balance FROM accounts WHERE customer_id=?",
                             (customer_id,)).fetchall()
        return json.dumps([dict(r) for r in rows])

    @tool
    def list_transactions(account_id: str, start_date: str = "", end_date: str = "",
                          category: str = "", limit: int = 20) -> str:
        """List transactions of one of the customer's accounts, newest first.
        Dates are YYYY-MM-DD (inclusive, optional). category is optional, for example
        groceries, dining, transport, entertainment, utilities, salary, fees, shopping.
        Negative amounts are spending, positive amounts are money in."""
        limit = max(1, min(int(limit), 50))
        with conn() as c:
            if not own_account(c, account_id):
                return "Error: account not found for this customer."
            sql, args = "SELECT * FROM transactions WHERE account_id=?", [account_id]
            if start_date:
                sql += " AND date>=?"; args.append(start_date)
            if end_date:
                sql += " AND date<=?"; args.append(end_date)
            if category:
                sql += " AND category=?"; args.append(category)
            sql += " ORDER BY date DESC, txn_id DESC LIMIT ?"; args.append(limit)
            rows = c.execute(sql, args).fetchall()
        return json.dumps([dict(r) for r in rows])

    @tool
    def spending_summary(account_id: str, start_date: str, end_date: str) -> str:
        """Total spending per category for one account between two dates (YYYY-MM-DD, inclusive).
        Use this for any 'how much did I spend' question instead of adding numbers yourself."""
        with conn() as c:
            if not own_account(c, account_id):
                return "Error: account not found for this customer."
            rows = c.execute(
                "SELECT category, ROUND(-SUM(amount),2) AS spent, COUNT(*) AS n FROM transactions "
                "WHERE account_id=? AND date>=? AND date<=? AND amount<0 GROUP BY category "
                "ORDER BY spent DESC", (account_id, start_date, end_date)).fetchall()
        return json.dumps([dict(r) for r in rows])

    @tool
    def search_policy(query: str) -> str:
        """Search the bank's policy documents (fees, disputes, card fraud, transfers, overdraft).
        Use this for any question about rules, fees, limits or procedures. Returns excerpts with
        their source file; cite the source file name in your answer."""
        s = store or rag.get_store()
        docs = rag.search(s, query, k=3)
        return "\n\n".join(f"[source: {d.metadata['source']}]\n{d.page_content}" for d in docs)

    @tool
    def create_dispute_ticket(txn_id: str, reason: str) -> str:
        """Open a dispute ticket for one of the customer's transactions. This changes data, so a
        human must approve it before it runs. Needs the transaction ID and a short reason."""
        with conn() as c:
            row = c.execute(
                "SELECT t.txn_id FROM transactions t JOIN accounts a ON a.account_id=t.account_id "
                "WHERE t.txn_id=? AND a.customer_id=?", (txn_id, customer_id)).fetchone()
            if row is None:
                return "Error: transaction not found for this customer."
            ticket = "D" + uuid.uuid4().hex[:6].upper()
            c.execute("INSERT INTO disputes VALUES (?,?,?,?,?,?)",
                      (ticket, txn_id, customer_id, reason, "OPEN",
                       datetime.now().isoformat(timespec="seconds")))
        return f"Dispute ticket {ticket} opened for transaction {txn_id}."

    return [list_accounts, list_transactions, spending_summary, search_policy, create_dispute_ticket]


# Tools that need human approval (write operations)
APPROVAL_REQUIRED = ["create_dispute_ticket"]
