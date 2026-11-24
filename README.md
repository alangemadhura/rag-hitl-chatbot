# IT Service Desk Multi-Agent Chatbot (RAG + Human-in-the-Loop)

A local, stateful, multi-agent chatbot that answers IT policy questions from a private knowledge base (RAG with citations) and executes operational actions (tickets, restarts, privileged access) only after human approval. It runs 100% locally with Ollama and ChromaDB, orchestrated as a LangGraph state machine.

## Features

- **Supervisor/router** using structured output (`general` / `rag` / `action`)
- **RAG agent** with relevance grading, one query rewrite, and exact citations (`[Source: file, Section]`)
- **Refusal instead of hallucination** when the knowledge base has no answer
- **Action planner** that fills tool arguments from the whole conversation (e.g. "open a ticket for *that*")
- **HITL approval gate** (`interrupt_before=["tool_executor"]`) with Approve / Edit arguments / Reject
- **Persistent memory** via SQLite checkpointer and `--thread-id`
- **Idempotent ingestion** using deterministic chunk IDs
- **Streaming** of node transitions in the CLI

## Tech stack

Python 3.10+, LangChain, LangGraph, Ollama (`llama3.1`, `nomic-embed-text`), ChromaDB, Pydantic, SQLite.

## Project structure

```
project2_rag_chatbot/
├── data/                  # 5 knowledge base documents (.md)
├── agents/
│   ├── state.py           # AgentChatState
│   ├── tools.py           # @tool functions, validation, impact summaries
│   ├── nodes.py           # supervisor, RAG, planner, executor, direct responder
│   └── graph.py           # graph wiring + checkpointer
├── ingest.py              # chunking, metadata, idempotent ChromaDB indexing
├── app.py                 # CLI runner (streaming, --thread-id, HITL prompts)
├── requirements.txt
└── README.md
```

## Setup

1. Install [Ollama](https://ollama.com) and pull the models:
   ```bash
   ollama pull llama3.1
   ollama pull nomic-embed-text
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```
3. Index the documents (safe to re-run; it will not create duplicates):
   ```bash
   python ingest.py
   ```
4. Start the chatbot:
   ```bash
   python app.py --thread-id demo1
   ```
   Re-run with the same `--thread-id` to resume a previous session.

## Architecture

```
[START]
   |
   v
[Supervisor / Triage]  (structured output)
   |-- general --> [Direct Responder] --> END
   |-- rag ------> [RAG Agent] ---------> END
   |                 retrieve -> grade -> (rewrite once) -> answer + citations
   '-- action ---> [Action Planner]
                         |
                (HITL interrupt: Approve / Edit / Reject)
                         |
                         v
                  [Tool Executor] --> END
```

Each turn ends at END and the next user message re-enters at the Supervisor. The SQLite checkpointer keeps the full state, so context and pending approvals persist across turns and restarts.

### Shared state

```python
class AgentChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Literal["general", "rag", "action"]
    retrieved_docs: list[dict]
    pending_action: Optional[dict]      # tool, args, impact
    approval_status: Optional[Literal["approved", "edited", "rejected"]]
```

### Tools (simulated side effects, logged to `actions_log.json`)

| Tool | Purpose |
|---|---|
| `create_ticket` | Opens a ticket, routed to a queue by priority P1-P4 |
| `request_server_restart` | Requests a service restart (warns about dropped sessions in production) |
| `request_jit_access` | Requests time-boxed privileged access (max 8h) |

All arguments are validated with Pydantic **before** the human sees them.

## Sample transcripts

### 1. Grounded RAG answer with citation

```
You: What is the acknowledgment time for a SEV-1 incident?
  -> [Supervisor] intent=rag
  -> [RAG Agent]

Assistant: The acknowledgment time for a SEV-1 incident is within **10 minutes**.
[Source: 01_incident_response_runbook.md, Section 1: Severity Classification & Response SLAs]
```

### 2. Action paused for human approval, then approved

```
You: Open a P2 ticket: VPN is down for the finance team
  -> [Supervisor] intent=action
  -> [Action Planner]

Assistant: I've prepared 'create_ticket'. Awaiting your approval.

============================================================
  [Awaiting Approval]  ACTION PAUSED FOR HUMAN REVIEW
============================================================
Tool   : create_ticket
Args   :
   summary = VPN down for finance team
   priority = P2
   impact = Not specified
Impact : Creates a P2 ticket routed to 'it-service-desk-tier2'.
============================================================
[a]pprove / [e]dit args / [r]eject: a
  -> [Tool Executor]

Assistant: Done. Ticket TCK-F62498 created (priority P2, queue it-service-desk-tier2).
```

### 3. Edited arguments (PASTE YOUR OWN TRANSCRIPT HERE)

```
(paste the terminal output of an action where you typed "e" and changed priority to P1)
```

### 4. Rejected action (PASTE YOUR OWN TRANSCRIPT HERE)

```
(paste the terminal output of an action where you typed "r")
```

## Design notes

- **Relevance check:** retrieved chunks are graded; if irrelevant, the query is rewritten once and re-retrieved. If still irrelevant, the bot says the knowledge base lacks the answer.
- **Deterministic IDs:** each chunk ID is a SHA-1 of `source|section|index`, so re-running `ingest.py` updates records instead of duplicating them.
- **Safety:** actions follow the human sign-off rules from the Access Control policy (restarts, IAM changes, P1 escalations).
- **Local-model robustness:** structured-output calls have fallbacks, and tool arguments are re-validated before execution.

## Limitations

- Small local models can occasionally misclassify intent or choose odd ticket details; the HITL edit step exists to catch this.
- Tools are simulated (JSON log), not connected to a real ticketing system.