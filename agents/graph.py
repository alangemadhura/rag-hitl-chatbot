import sqlite3

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END

from agents.nodes import build_nodes
from agents.state import AgentChatState


def build_graph(model: str = "llama3.1", db_dir: str = "chroma_db",
                memory_file: str = "chat_memory.sqlite"):
    llm = ChatOllama(model=model, temperature=0)
    vs = Chroma(
        collection_name="it_kb",
        embedding_function=OllamaEmbeddings(model="nomic-embed-text"),
        persist_directory=db_dir,
    )
    nodes = build_nodes(llm, vs)

    g = StateGraph(AgentChatState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        lambda s: s["intent"],
        {"general": "direct", "rag": "rag", "action": "planner"},
    )
    g.add_conditional_edges(
        "planner",
        lambda s: "tool_executor" if s.get("pending_action") else END,
        {"tool_executor": "tool_executor", END: END},
    )
    g.add_edge("direct", END)
    g.add_edge("rag", END)
    g.add_edge("tool_executor", END)

    conn = sqlite3.connect(memory_file, check_same_thread=False)
    saver = SqliteSaver(conn)
    return g.compile(checkpointer=saver, interrupt_before=["tool_executor"])
