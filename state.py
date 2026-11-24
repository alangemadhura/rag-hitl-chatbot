from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Literal["general", "rag", "action"]
    retrieved_docs: list[dict]          # content, source, section, score
    pending_action: Optional[dict]      # {"tool", "args", "impact"}
    approval_status: Optional[Literal["approved", "edited", "rejected"]]