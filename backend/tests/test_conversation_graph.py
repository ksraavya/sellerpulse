from langchain_core.messages import HumanMessage

from app.conversations.graph import ConversationGraph, DEFAULT_GREETING


def test_new_session_greets_once_and_stores_initial_state(tmp_path):
    graph = ConversationGraph(tmp_path / "sessions.sqlite3")
    try:
        result = graph.create_session("session-1", "demo-seller")
        assert result["session_id"] == "session-1"
        assert result["seller_id"] == "demo-seller"
        assert result["status"] == "active"
        assert result["messages"] == [
            {"role": "assistant", "content": DEFAULT_GREETING}
        ]
        assert result["current_intent"] == "greeting"
    finally:
        graph.close()


def test_message_is_appended_to_existing_session(tmp_path):
    graph = ConversationGraph(tmp_path / "sessions.sqlite3")
    try:
        graph.create_session("session-2", "demo-seller")
        result = graph.send_message("session-2", "My sales have fallen.")
        assert result is not None
        assert result["messages"][0]["content"] == DEFAULT_GREETING
        assert result["messages"][1] == {
            "role": "seller",
            "content": "My sales have fallen.",
        }
        assert result["messages"][2]["role"] == "assistant"
    finally:
        graph.close()


def test_session_state_survives_graph_recreation(tmp_path):
    database = tmp_path / "persistent.sqlite3"
    first = ConversationGraph(database)
    first.create_session("persistent-session", "demo-seller")
    first.send_message("persistent-session", "I am seeing more cancellations.")
    first.close()

    second = ConversationGraph(database)
    try:
        result = second.get_session("persistent-session")
        assert result is not None
        assert any(
            item["content"] == "I am seeing more cancellations."
            and item["role"] == "seller"
            for item in result["messages"]
        )
    finally:
        second.close()


def test_unknown_session_returns_none(tmp_path):
    graph = ConversationGraph(tmp_path / "sessions.sqlite3")
    try:
        assert graph.get_session("missing") is None
        assert graph.send_message("missing", "Hello") is None
    finally:
        graph.close()
