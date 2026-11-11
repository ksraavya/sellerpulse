from fastapi.testclient import TestClient

from app.main import app
from app.conversations.graph import get_conversation_graph


def test_conversation_api_greeting_and_message(tmp_path, monkeypatch):
    from app.conversations import graph as graph_module
    test_graph = graph_module.ConversationGraph(tmp_path / "api.sqlite3")
    monkeypatch.setattr(graph_module, "_graph", test_graph)
    client = TestClient(app)
    try:
        created = client.post(
            "/api/conversations", json={"seller_id": "demo-seller"}
        )
        assert created.status_code == 201
        body = created.json()
        session_id = body["session_id"]
        assert body["messages"][0]["role"] == "assistant"
        assert "Welcome to SellerPulse" in body["response"]

        sent = client.post(
            f"/api/conversations/{session_id}/messages",
            json={"content": "My sales are declining."},
        )
        assert sent.status_code == 200
        assert sent.json()["messages"][-2]["content"] == "My sales are declining."

        fetched = client.get(f"/api/conversations/{session_id}")
        assert fetched.status_code == 200
        assert len(fetched.json()["messages"]) == 3
    finally:
        test_graph.close()


def test_unknown_seller_cannot_start_session():
    client = TestClient(app)
    response = client.post(
        "/api/conversations", json={"seller_id": "not-a-real-seller"}
    )
    assert response.status_code == 404


def test_unknown_session_returns_404():
    client = TestClient(app)
    response = client.get("/api/conversations/not-a-session")
    assert response.status_code == 404
