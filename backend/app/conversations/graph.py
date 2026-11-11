"""SP-06A conversation graph foundation: session greeting and message capture."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.conversations.state import ConversationState

DEFAULT_GREETING = (
    "Hey! Welcome to SellerPulse. I'm your virtual Key Account Manager. "
    "How are things going with your business today? Is there something "
    "specific you'd like us to look into, or would you like a quick "
    "overview of your store's performance?"
)


class ConversationGraph:
    """Owns graph compilation, checkpoint persistence and session operations."""

    def __init__(self, database_path: str | Path = "data/conversations.sqlite3") -> None:
        path = Path(database_path).expanduser()
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._checkpointer = SqliteSaver(self._connection)
        self._checkpointer.setup()
        builder = StateGraph(ConversationState)
        builder.add_node("greet", self._greet)
        builder.add_node("capture_message", self._capture_message)
        builder.add_edge(START, "greet")
        builder.add_edge("greet", END)
        # Message capture is intentionally a temporary SP-06A node. Intent
        # routing and specialised agent dispatch arrive in SP-06B onward.
        self._message_builder = StateGraph(ConversationState)
        self._message_builder.add_node("capture_message", self._capture_message)
        self._message_builder.add_edge(START, "capture_message")
        self._message_builder.add_edge("capture_message", END)
        self._session_graph = builder.compile(checkpointer=self._checkpointer)
        self._message_graph = self._message_builder.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _greet(state: ConversationState) -> dict[str, Any]:
        if state.get("greeted"):
            return {}
        return {
            "messages": [AIMessage(content=DEFAULT_GREETING)],
            "greeted": True,
            "status": "active",
            "response": DEFAULT_GREETING,
        }

    @staticmethod
    def _capture_message(state: ConversationState) -> dict[str, Any]:
        # This is deliberately not an intent router yet. It preserves the
        # incoming turn and gives a truthful acknowledgement until SP-06B.
        latest = next(
            (message for message in reversed(state.get("messages", []))
             if isinstance(message, HumanMessage)),
            None,
        )
        content = latest.content if latest else ""
        response = (
            "Thanks for sharing that. I'll keep it in mind as we look at "
            "your store's performance together."
        )
        return {
            "response": response,
            "current_intent": state.get("current_intent") or "unclassified",
            "messages": [AIMessage(content=response)],
        }

    def create_session(self, session_id: str, seller_id: str) -> dict[str, Any]:
        config = {"configurable": {"thread_id": session_id}}
        result = self._session_graph.invoke(
            {
                "session_id": session_id,
                "seller_id": seller_id,
                "messages": [],
                "greeted": False,
                "status": "active",
                "current_intent": "greeting",
                "diagnostic_findings": [],
                "context_observations": [],
                "pending_questions": [],
                "answered_questions": [],
                "unresolved_issues": [],
                "recommendations": [],
                "recommendation_round": 0,
                "question_count": 0,
            },
            config,
        )
        return self._snapshot(result)

    def send_message(self, session_id: str, content: str) -> dict[str, Any] | None:
        config = {"configurable": {"thread_id": session_id}}
        current = self._session_graph.get_state(config)
        if not current.values:
            return None
        result = self._message_graph.invoke(
            {"messages": [HumanMessage(content=content)]}, config
        )
        return self._snapshot(result)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        snapshot = self._session_graph.get_state(
            {"configurable": {"thread_id": session_id}}
        )
        if not snapshot.values:
            return None
        return self._snapshot(snapshot.values)

    @staticmethod
    def _snapshot(state: dict[str, Any]) -> dict[str, Any]:
        messages = []
        for message in state.get("messages", []):
            role = "seller" if isinstance(message, HumanMessage) else "assistant"
            messages.append({"role": role, "content": message.content})
        return {
            "session_id": state.get("session_id"),
            "seller_id": state.get("seller_id"),
            "status": state.get("status", "active"),
            "messages": messages,
            "response": state.get("response"),
            "current_intent": state.get("current_intent"),
        }

    def close(self) -> None:
        self._connection.close()


_graph: ConversationGraph | None = None


def get_conversation_graph() -> ConversationGraph:
    global _graph
    if _graph is None:
        database_path = os.getenv("CONVERSATION_DB_PATH", "data/conversations.sqlite3")
        _graph = ConversationGraph(database_path)
    return _graph
