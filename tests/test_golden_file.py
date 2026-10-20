"""不调用模型，只检查评估集本身格式正确、引用的工具和客户都存在。"""
import json
from pathlib import Path

from bankbot.tools import build_tools

GOLDEN = Path(__file__).resolve().parents[1] / "eval" / "golden.jsonl"


def test_golden_is_wellformed(db):
    names = {t.name for t in build_tools("C001", db_path=db)}
    ids = set()
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        assert c["id"] not in ids
        ids.add(c["id"])
        assert c["customer"] in {"C001", "C002", "C003"}
        for t in c.get("expect_tools", []) + c.get("forbid_tools", []):
            assert t in names
