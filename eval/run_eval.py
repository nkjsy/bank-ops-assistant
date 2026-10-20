"""Run the eval set: python eval/run_eval.py [--limit N] [--model deepseek:deepseek-chat]

Each case checks: whether the expected tools were called, whether the answer has the key info, whether data that shouldn't be seen leaked,
and whether the DB was (or wasn't) written after approval. Results go to eval/reports/ and the pass rate is printed.
"""
import argparse
import json
import re
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankbot import config, data_gen, rag  # noqa: E402
from bankbot.agent import ask, build_agent, final_text, tools_called  # noqa: E402
from bankbot.llm import get_llm  # noqa: E402


def run_case(case, llm, store, db_path):
    agent = build_agent(case["customer"], llm=llm, store=store, db_path=db_path)
    decision = case.get("human_decision", "reject")
    decide = lambda r: {"type": "approve"} if decision == "approve" else {"type": "reject", "message": "rejected"}
    before = sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM disputes").fetchone()[0]
    result = ask(agent, case["question"], uuid.uuid4().hex, decide=decide)
    after = sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM disputes").fetchone()[0]

    text, called, fails = final_text(result), tools_called(result), []
    for t in case.get("expect_tools", []):
        if t not in called:
            fails.append(f"did not call tool {t}")
    for t in case.get("forbid_tools", []):
        if t in called:
            fails.append(f"should not have called tool {t}")
    for rx in case.get("answer_regex", []):
        if not re.search(rx, text, re.I):
            fails.append(f"answer does not match /{rx}/")
    for rx in case.get("answer_not_regex", []):
        if re.search(rx, text, re.I):
            fails.append(f"answer leaked /{rx}/")
    if "expect_dispute" in case and (after > before) != case["expect_dispute"]:
        fails.append(f"ticket creation differs from expectation (expected {case['expect_dispute']})")
    return {"id": case["id"], "pass": not fails, "fails": fails, "tools": called, "answer": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--model")
    args = ap.parse_args()

    cases = [json.loads(l) for l in (ROOT / "eval" / "golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = cases[: args.limit] if args.limit else cases
    llm = get_llm(args.model)
    model_name = args.model or config.LLM_MODEL

    with tempfile.TemporaryDirectory() as tmp:
        store = rag.build_index(persist_dir=Path(tmp) / "chroma")
        results = []
        for c in cases:
            db_path = data_gen.generate(Path(tmp) / f"{c['id']}.db")  # a fresh DB per case so they don't affect each other
            r = run_case(c, llm, store, db_path)
            results.append(r)
            print(("PASS" if r["pass"] else "FAIL"), c["id"], r["fails"] or "")

    passed = sum(r["pass"] for r in results)
    print(f"\nPassed {passed}/{len(results)} = {passed / len(results):.0%}  (model {model_name})")

    out = ROOT / "eval" / "reports"
    out.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    lines = [f"# Eval {stamp}", f"Model: {model_name}", f"Pass rate: {passed}/{len(results)}", "",
             "| Case | Result | Tools called | Issues |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['id']} | {'PASS' if r['pass'] else 'FAIL'} | {', '.join(r['tools'])} | {'; '.join(r['fails'])} |")
    (out / f"{stamp}.md").write_text("\n".join(lines), encoding="utf-8")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
