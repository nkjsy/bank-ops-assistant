"""Generate synthetic bank data (all fictional): customers, accounts, transactions, written to SQLite.

The random seed is fixed, so the data is identical every run. A few "storyline" transactions are planted on purpose,
used by the eval set (eval/golden.jsonl):
  - T9001 / T9002: C001 was double-charged by StreamFlix (to demo filing a dispute)
  - T9003 / T9004: C001's overseas purchase and the matching 3% fee
  - T9101: C002's unique merchant BlueBottle (to test unauthorized access: C001 must not see it)
"""
import random
import sqlite3
from datetime import date, timedelta

from . import config

CUSTOMERS = [
    ("C001", "Alex Morgan"),
    ("C002", "Sam Rivera"),
    ("C003", "Jordan Lee"),
]
ACCOUNTS = [  # account_id, customer_id, type
    ("A001", "C001", "chequing"),
    ("A002", "C001", "savings"),
    ("A003", "C002", "chequing"),
    ("A004", "C002", "savings"),
    ("A005", "C003", "chequing"),
]
MERCHANTS = {
    "groceries": ["FreshMart", "GreenGrocer", "DailyBasket"],
    "dining": ["Corner Cafe", "Noodle House", "Burger Barn"],
    "transport": ["CityRide", "FuelStop"],
    "entertainment": ["CineMax", "GameHub"],
    "utilities": ["PowerCo", "NetConnect"],
}

SCHEMA = """
DROP TABLE IF EXISTS customers; DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS transactions; DROP TABLE IF EXISTS disputes;
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT);
CREATE TABLE accounts (account_id TEXT PRIMARY KEY, customer_id TEXT, type TEXT, balance REAL);
CREATE TABLE transactions (
  txn_id TEXT PRIMARY KEY, account_id TEXT, date TEXT,
  description TEXT, category TEXT, amount REAL);  -- spending is negative, income is positive
CREATE TABLE disputes (
  ticket_id TEXT PRIMARY KEY, txn_id TEXT, customer_id TEXT,
  reason TEXT, status TEXT, created_at TEXT);
"""


def generate(db_path=None):
    db_path = db_path or config.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    end = date.fromisoformat(config.AS_OF_DATE) - timedelta(days=1)
    start = end - timedelta(days=60)

    rows = []
    n = 0
    for acc_id, _cust, kind in ACCOUNTS:
        if kind == "savings":
            rows.append((f"S{acc_id}", acc_id, "2026-09-01", "Monthly interest", "interest", 12.5))
            continue
        d = start
        while d <= end:
            if d.day == 1:  # salary is paid on the 1st of each month
                n += 1
                rows.append((f"T{n:04d}", acc_id, d.isoformat(), "Salary", "salary", 3200.0))
            for _ in range(rng.choice([0, 1, 1, 2])):
                n += 1
                cat = rng.choice(list(MERCHANTS))
                rows.append((f"T{n:04d}", acc_id, d.isoformat(), rng.choice(MERCHANTS[cat]),
                             cat, -round(rng.uniform(4, 120), 2)))
            d += timedelta(days=1)

    # storyline transactions
    rows += [
        ("T9001", "A001", "2026-09-12", "StreamFlix", "entertainment", -15.99),
        ("T9002", "A001", "2026-09-12", "StreamFlix", "entertainment", -15.99),
        ("T9003", "A001", "2026-09-20", "TokyoMart (JPY)", "shopping", -150.00),
        ("T9004", "A001", "2026-09-20", "International Transaction Fee", "fees", -4.50),
        ("T9101", "A003", "2026-09-15", "BlueBottle Coffee Roasters", "dining", -42.00),
    ]

    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO customers VALUES (?,?)", CUSTOMERS)
    con.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?)", rows)
    for acc_id, cust, kind in ACCOUNTS:
        total = con.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account_id=?",
                            (acc_id,)).fetchone()[0]
        opening = 1000.0 if kind == "chequing" else 5000.0
        con.execute("INSERT INTO accounts VALUES (?,?,?,?)", (acc_id, cust, kind, round(opening + total, 2)))
    con.commit()
    con.close()
    return db_path


if __name__ == "__main__":
    p = generate()
    print(f"Database generated: {p}")
