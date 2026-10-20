"""跑评估集： python eval/run_eval.py [--limit N] [--model deepseek:deepseek-chat]

每条用例检查：该调的工具调了没有、答案里有没有关键信息、有没有泄露不该看的数据、
审批后是否真的（没）写库。结果写进 eval/reports/，并打印通过率。
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
            fails.append(f"没调用工具 {t}")
    for t in case.get("forbid_tools", []):
        if t in called:
            fails.append(f"不该调用工具 {t}")
    for rx in case.get("answer_regex", []):
        if not re.search(rx, text, re.I):
            fails.append(f"答案里没找到 /{rx}/")
    for rx in case.get("answer_not_regex", []):
        if re.search(rx, text, re.I):
            fails.append(f"答案泄露了 /{rx}/")
    if "expect_dispute" in case and (after > before) != case["expect_dispute"]:
        fails.append(f"工单创建与预期不符（预期 {case['expect_dispute']}）")
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
            db_path = data_gen.generate(Path(tmp) / f"{c['id']}.db")  # 每条用例一份新库，互不影响
            r = run_case(c, llm, store, db_path)
            results.append(r)
            print(("PASS" if r["pass"] else "FAIL"), c["id"], r["fails"] or "")

    passed = sum(r["pass"] for r in results)
    print(f"\n通过 {passed}/{len(results)} = {passed / len(results):.0%}  （模型 {model_name}）")

    out = ROOT / "eval" / "reports"
    out.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    lines = [f"# Eval {stamp}", f"模型：{model_name}", f"通过率：{passed}/{len(results)}", "",
             "| 用例 | 结果 | 调用的工具 | 问题 |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['id']} | {'PASS' if r['pass'] else 'FAIL'} | {', '.join(r['tools'])} | {'; '.join(r['fails'])} |")
    (out / f"{stamp}.md").write_text("\n".join(lines), encoding="utf-8")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
