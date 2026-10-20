"""Command-line chat: python -m bankbot.cli --customer C001"""
import argparse
import uuid

from . import config, data_gen, rag
from .agent import ask, build_agent, final_text
from .guardrails import screen_input


def ask_human(req):
    print(f"\n[Approval needed] agent wants to run: {req['name']}  args: {req['args']}")
    ans = input("Approve? (y=approve / n=reject) > ").strip().lower()
    if ans == "y":
        return {"type": "approve"}
    return {"type": "reject", "message": "The customer's reviewer rejected this action."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--customer", default="C001", help="Which customer to chat as: C001 / C002 / C003")
    args = p.parse_args()

    if not config.DB_PATH.exists():
        data_gen.generate()
    if not config.CHROMA_DIR.exists():
        print("First run, building the RAG index (downloads a ~80MB local embedding model)...")
        rag.build_index()

    agent = build_agent(args.customer)
    thread = uuid.uuid4().hex
    print(f"Logged in as customer {args.customer}. Type a question, or q to quit.")
    while True:
        q = input("\nYou> ").strip()
        if q.lower() in {"q", "quit", "exit"}:
            break
        if not q:
            continue
        clean, flags = screen_input(q)
        if flags:
            print(f"[Guardrail warning] suspicious instructions in input: {flags} (tool scope limits still apply)")
        result = ask(agent, clean, thread, decide=ask_human)
        print(f"\nAssistant> {final_text(result)}")


if __name__ == "__main__":
    main()
