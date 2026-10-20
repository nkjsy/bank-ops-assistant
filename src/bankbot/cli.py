"""命令行聊天： python -m bankbot.cli --customer C001"""
import argparse
import uuid

from . import config, data_gen, rag
from .agent import ask, build_agent, final_text
from .guardrails import screen_input


def ask_human(req):
    print(f"\n[需要审批] agent 想执行：{req['name']}  参数：{req['args']}")
    ans = input("批准吗？(y=批准 / n=拒绝) > ").strip().lower()
    if ans == "y":
        return {"type": "approve"}
    return {"type": "reject", "message": "The customer's reviewer rejected this action."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--customer", default="C001", help="以哪个客户身份聊天，C001 / C002 / C003")
    args = p.parse_args()

    if not config.DB_PATH.exists():
        data_gen.generate()
    if not config.CHROMA_DIR.exists():
        print("第一次运行，正在建 RAG 索引（会下载一个约 80MB 的本地向量模型）...")
        rag.build_index()

    agent = build_agent(args.customer)
    thread = uuid.uuid4().hex
    print(f"已登录客户 {args.customer}。输入问题，输入 q 退出。")
    while True:
        q = input("\n你> ").strip()
        if q.lower() in {"q", "quit", "exit"}:
            break
        if not q:
            continue
        clean, flags = screen_input(q)
        if flags:
            print(f"[护栏提醒] 输入里有可疑指令：{flags}（工具权限限制仍然有效）")
        result = ask(agent, clean, thread, decide=ask_human)
        print(f"\n助手> {final_text(result)}")


if __name__ == "__main__":
    main()
