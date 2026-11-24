import json
import os
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from langchain_core.tools import tool

LOG_FILE = "actions_log.json"

QUEUES = {
    "P1": "it-incident-oncall",
    "P2": "it-service-desk-tier2",
    "P3": "it-service-desk-tier1",
    "P4": "it-general-support",
}


# ---------- Argument schemas (validated BEFORE the human sees them) ----------
class TicketArgs(BaseModel):
    summary: str = Field(min_length=5)
    priority: Literal["P1", "P2", "P3", "P4"]
    impact: str = Field(default="Not specified", min_length=3)


class RestartArgs(BaseModel):
    service: str = Field(min_length=2)
    environment: Literal["production", "staging", "development"]
    reason: str = Field(min_length=5)


class JitArgs(BaseModel):
    role: Literal["prod-db-readonly", "k8s-admin", "iam-elevated"]
    ticket_ref: str = Field(min_length=3)
    hours: int = Field(default=4, ge=1, le=8)


# ---------- Simulated side effects (written to a JSON log) ----------
def _log(entry: dict):
    data = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    entry["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@tool(args_schema=TicketArgs)
def create_ticket(summary: str, priority: str, impact: str = "Not specified") -> str:
    """Create a service desk ticket and route it to the right queue by priority."""
    ticket_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"
    queue = QUEUES[priority]
    _log({"action": "create_ticket", "ticket_id": ticket_id, "summary": summary,
          "priority": priority, "queue": queue, "impact": impact})
    return f"Ticket {ticket_id} created (priority {priority}, queue {queue})."


@tool(args_schema=RestartArgs)
def request_server_restart(service: str, environment: str, reason: str) -> str:
    """Submit a restart request for a service in a given environment."""
    req_id = f"RST-{uuid.uuid4().hex[:6].upper()}"
    _log({"action": "request_server_restart", "request_id": req_id, "service": service,
          "environment": environment, "reason": reason})
    return f"Restart request {req_id} submitted for {service} ({environment})."


@tool(args_schema=JitArgs)
def request_jit_access(role: str, ticket_ref: str, hours: int = 4) -> str:
    """Request Just-in-Time privileged access for a role."""
    req_id = f"JIT-{uuid.uuid4().hex[:6].upper()}"
    _log({"action": "request_jit_access", "request_id": req_id, "role": role,
          "ticket_ref": ticket_ref, "hours": hours})
    return f"JIT access {req_id} granted for role {role} for {hours}h (ref {ticket_ref})."


SCHEMAS = {
    "create_ticket": TicketArgs,
    "request_server_restart": RestartArgs,
    "request_jit_access": JitArgs,
}
TOOLS = {
    "create_ticket": create_ticket,
    "request_server_restart": request_server_restart,
    "request_jit_access": request_jit_access,
}
TOOL_NAMES = list(TOOLS)


# ---------- Helpers ----------
def validate_args(tool_name: str, args: dict) -> dict:
    """Return clean, typed args or raise ValidationError."""
    clean = {k: v for k, v in args.items() if v not in (None, "")}
    return SCHEMAS[tool_name].model_validate(clean).model_dump()


def format_errors(err: ValidationError) -> str:
    return "; ".join(f"{e['loc'][0] if e['loc'] else 'input'}: {e['msg']}" for e in err.errors())


def describe_impact(tool_name: str, args: dict) -> str:
    if tool_name == "create_ticket":
        q = QUEUES[args["priority"]]
        extra = " This is an URGENT ticket: confirm priority, queue and impact." if args["priority"] == "P1" else ""
        return f"Creates a {args['priority']} ticket routed to '{q}'.{extra}"
    if tool_name == "request_server_restart":
        warn = " May drop active sessions; explicit human approval required (Runbook s3, Security Policy s4)." \
            if args["environment"] == "production" else ""
        return f"Requests restart of '{args['service']}' in {args['environment']}.{warn}"
    if tool_name == "request_jit_access":
        return (f"Grants elevated role '{args['role']}' for {args['hours']}h "
                f"(max 8h). Privileged IAM change; human sign-off mandatory (Security Policy s4).")
    return "Unknown action."


def run_tool(tool_name: str, args: dict) -> str:
    return TOOLS[tool_name].invoke(args)