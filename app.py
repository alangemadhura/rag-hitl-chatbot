import argparse
import uuid

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from agents.graph import build_graph
from agents.tools import validate_args, describe_impact, format_errors

LABELS = {
    "supervisor": "[Supervisor]", "direct": "[Direct Responder]", "rag": "[RAG Agent]",
    "planner": "[Action Planner]", "tool_executor": "[Tool Executor]",
}


def run(graph, inp, config):
    """Stream node transitions and print assistant messages as they appear."""
    for chunk in graph.stream(inp, config, stream_mode="updates"):
        for node, update in chunk.items():
            update = update or {}
            extra = f" intent={update['intent']}" if "intent" in update else ""
            print(f"  -> {LABELS.get(node, node)}{extra}")
            for m in update.get("messages", []):
                print(f"\nAssistant: {m.content}\n")


def hitl_review(graph, config):
    snap = graph.get_state(config)
    pa = snap.values["pending_action"]
    print("\n" + "=" * 60)
    print("  [Awaiting Approval]  ACTION PAUSED FOR HUMAN REVIEW")
    print("=" * 60)
    print(f"Tool   : {pa['tool']}")
    print("Args   :")
    for k, v in pa["args"].items():
        print(f"   {k} = {v}")
    print(f"Impact : {pa['impact']}")
    print("=" * 60)

    while True:
        choice = input("[a]pprove / [e]dit args / [r]eject: ").strip().lower()
        if choice == "a":
            graph.update_state(config, {"approval_status": "approved"}, as_node="planner")
            break
        if choice == "r":
            graph.update_state(config, {"approval_status": "rejected"}, as_node="planner")
            break
        if choice == "e":
            new_args = dict(pa["args"])
            for k, v in pa["args"].items():
                val = input(f"  {k} [{v}]: ").strip()
                if val:
                    new_args[k] = val
            try:
                clean = validate_args(pa["tool"], new_args)
            except ValidationError as e:
                print(f"  Invalid: {format_errors(e)}. Try again.")
                continue
            new_pa = {"tool": pa["tool"], "args": clean,
                      "impact": describe_impact(pa["tool"], clean)}
            graph.update_state(config, {"pending_action": new_pa, "approval_status": "edited"},
                               as_node="planner")
            break
        print("Please type a, e or r.")

    run(graph, None, config)  # resume execution


def main():
    p = argparse.ArgumentParser(description="IT Service Desk multi-agent chatbot")
    p.add_argument("--thread-id", default=None, help="Resume an existing session")
    p.add_argument("--model", default="llama3.1")
    args = p.parse_args()

    graph = build_graph(model=args.model)
    thread_id = args.thread_id or f"session-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    print(f"Thread: {thread_id}   (resume later with --thread-id {thread_id})")
    print("Type 'exit' to quit.\n")

    while True:
        snap = graph.get_state(config)
        if snap.next and "tool_executor" in snap.next:   # paused action (also when resuming a thread)
            hitl_review(graph, config)
            continue
        text = input("You: ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if not text:
            continue
        run(graph, {"messages": [HumanMessage(content=text)]}, config)


if __name__ == "__main__":
    main()