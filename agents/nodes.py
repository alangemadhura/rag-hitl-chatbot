from typing import Literal, Optional

from pydantic import BaseModel, ValidationError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.tools import (
    validate_args, format_errors, describe_impact, run_tool,
)


# ---------- Structured output schemas ----------
class Route(BaseModel):
    intent: Literal["general", "rag", "action"]


class Grade(BaseModel):
    relevant: bool


class ActionPlan(BaseModel):
    tool: Literal["create_ticket", "request_server_restart", "request_jit_access", "none"]
    # create_ticket
    summary: Optional[str] = None
    priority: Optional[Literal["P1", "P2", "P3", "P4"]] = None
    impact: Optional[str] = None
    # request_server_restart
    service: Optional[str] = None
    environment: Optional[Literal["production", "staging", "development"]] = None
    reason: Optional[str] = None
    # request_jit_access
    role: Optional[Literal["prod-db-readonly", "k8s-admin", "iam-elevated"]] = None
    ticket_ref: Optional[str] = None
    hours: Optional[int] = None


# ---------- Helpers ----------
def history_text(messages, n: int = 6) -> str:
    lines = []
    for m in messages[-n:]:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)


def last_user_text(messages) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def plan_to_args(p: ActionPlan) -> dict:
    if p.tool == "create_ticket":
        return {"summary": p.summary, "priority": p.priority, "impact": p.impact}
    if p.tool == "request_server_restart":
        return {"service": p.service, "environment": p.environment, "reason": p.reason}
    if p.tool == "request_jit_access":
        return {"role": p.role, "ticket_ref": p.ticket_ref, "hours": p.hours}
    return {}


def build_nodes(llm, vectorstore, k: int = 4):
    router = llm.with_structured_output(Route)
    grader = llm.with_structured_output(Grade)
    planner = llm.with_structured_output(ActionPlan)

    # ---------- Supervisor ----------
    def supervisor_node(state):
        prompt = (
            "Classify the user's LATEST message into one intent.\n"
            "- general: greetings, thanks, small talk, questions about the conversation itself.\n"
            "- rag: questions about IT policies, runbooks, SLAs, procedures, rules (lookup in knowledge base).\n"
            "- action: the user asks to DO something that changes state: open/create a ticket, "
            "restart a server/service, request privileged access. Phrases like 'go ahead and open a ticket "
            "for that' are action.\n\n"
            f"Conversation:\n{history_text(state['messages'])}"
        )
        try:
            intent = router.invoke(prompt).intent
        except Exception:
            intent = "rag"
        return {"intent": intent}

    # ---------- Direct responder ----------
    def direct_node(state):
        sys = SystemMessage(content="You are a friendly IT Service Desk assistant. Keep answers short.")
        res = llm.invoke([sys] + state["messages"])
        return {"messages": [AIMessage(content=res.content)]}

    # ---------- RAG agent ----------
    def retrieve(query: str):
        results = vectorstore.similarity_search_with_score(query, k=k)
        return [{
            "content": d.page_content,
            "source": d.metadata.get("source", "?"),
            "section": d.metadata.get("section", "?"),
            "score": float(score),
        } for d, score in results]

    def is_relevant(question: str, docs: list) -> bool:
        if not docs:
            return False
        ctx = "\n---\n".join(d["content"] for d in docs)
        prompt = (
            f"Question: {question}\n\nRetrieved context:\n{ctx}\n\n"
            "Does the context contain information that helps answer the question, "
            "even partially? Reply with one word only: YES or NO."
        )
        try:
            ans = llm.invoke(prompt).content.strip().upper()
            return not ans.startswith("NO")
        except Exception:
            return True

    def rag_node(state):
        question = last_user_text(state["messages"])
        docs = retrieve(question)

        if not is_relevant(question, docs):
            rewrite_prompt = (
                "Rewrite the user's last question as a standalone search query for an IT policy "
                "knowledge base, using the conversation for context. Reply with the query only.\n\n"
                f"Conversation:\n{history_text(state['messages'])}"
            )
            q2 = llm.invoke(rewrite_prompt).content.strip()
            docs = retrieve(q2)
            if not is_relevant(question, docs):
                msg = ("I couldn't find an answer to that in the knowledge base, so I won't guess. "
                       "Try rephrasing, or ask about incidents, access control, deployments, "
                       "ticketing/SLAs, or onboarding.")
                return {"messages": [AIMessage(content=msg)], "retrieved_docs": []}

        ctx = "\n\n".join(
            f"[Source: {d['source']}, {d['section']}]\n{d['content']}" for d in docs
        )
        prompt = (
            "Answer the question using ONLY the context below. After each fact, cite the source in "
            "exactly this format: [Source: <filename>, <section>]. If the context only partly answers, "
            "say what is missing.\n\n"
            f"Context:\n{ctx}\n\nQuestion: {question}"
        )
        answer = llm.invoke(prompt).content
        return {"messages": [AIMessage(content=answer)], "retrieved_docs": docs}

    # ---------- Action planner ----------
    def planner_node(state):
        prompt = (
            "Choose ONE action tool for the user's request, using the whole conversation for details "
            "(e.g. 'that' refers to earlier messages). Tools:\n"
            "- create_ticket: summary, priority (P1 = production outage/security incident affecting many users; "
            "P2 = high / blocking a deadline; P3 = normal; P4 = low), impact.\n"
            "- request_server_restart: service, environment (production/staging/development), reason.\n"
            "- request_jit_access: role (prod-db-readonly/k8s-admin/iam-elevated), ticket_ref, hours (max 8).\n"
            "If the user says 'high priority', use P2 unless it is an outage (then P1). "
            "Leave unknown fields empty; never invent values. Use tool 'none' if no tool fits.\n\n"
            f"Conversation:\n{history_text(state['messages'], 8)}"
        )
        try:
            plan = planner.invoke(prompt)
        except Exception:
            plan = ActionPlan(tool="none")

        if plan.tool == "none":
            return {"pending_action": None, "approval_status": None,
                    "messages": [AIMessage(content="I couldn't tell which action you want. "
                                                   "I can open tickets, request server restarts, or request JIT access.")]}
        try:
            args = validate_args(plan.tool, plan_to_args(plan))
        except ValidationError as e:
            return {"pending_action": None, "approval_status": None,
                    "messages": [AIMessage(content=f"I need more valid details before I can prepare "
                                                   f"'{plan.tool}': {format_errors(e)}")]}

        impact = describe_impact(plan.tool, args)
        return {
            "pending_action": {"tool": plan.tool, "args": args, "impact": impact},
            "approval_status": None,
            "messages": [AIMessage(content=f"I've prepared '{plan.tool}'. Awaiting your approval.")],
        }

    # ---------- Tool executor (runs only after the HITL pause) ----------
    def tool_executor_node(state):
        pa = state.get("pending_action")
        status = state.get("approval_status")
        if not pa:
            return {"messages": [AIMessage(content="Nothing to execute.")]}
        if status == "rejected":
            return {"pending_action": None,
                    "messages": [AIMessage(content="No problem, I've cancelled that action. Nothing was changed.")]}
        try:
            args = validate_args(pa["tool"], pa["args"])
            result = run_tool(pa["tool"], args)
        except ValidationError as e:
            return {"pending_action": None,
                    "messages": [AIMessage(content=f"Action failed validation: {format_errors(e)}")]}
        return {"pending_action": None,
                "messages": [AIMessage(content=f"Done. {result}")]}

    return {
        "supervisor": supervisor_node,
        "direct": direct_node,
        "rag": rag_node,
        "planner": planner_node,
        "tool_executor": tool_executor_node,
    }
