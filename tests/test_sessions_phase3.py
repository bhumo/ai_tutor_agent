"""Phase-three persistence, ownership, and session-flow tests."""

from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

import main
from auth.routes import get_current_user
from database.models import Base, ChatMessage, User, get_db
from rag.schemas import AnswerSource, Citation, TutorAnswer, TutorDomain
from sessions.service import SessionService


@pytest.fixture
def session_client(tmp_path: Path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'sessions.db'}", connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)
    db = TestSession()
    users = {
        "a": User(id="user-a", email="a@example.com", hashed_password="unused"),
        "b": User(id="user-b", email="b@example.com", hashed_password="unused"),
    }
    db.add_all(users.values())
    db.commit()
    selected = {"user": users["a"]}

    def override_db():
        test_db = TestSession()
        try:
            yield test_db
        finally:
            test_db.close()

    main.app.dependency_overrides[get_db] = override_db
    main.app.dependency_overrides[get_current_user] = lambda: selected["user"]
    main.chat_rate_limiter.clear()
    monkeypatch.setattr(main, "CHAT_RATE_LIMIT", 100)
    monkeypatch.setattr(main.workflow, "process", lambda message: TutorAnswer(
        answer=f"Tutor response to: {message}",
        route="rag",
        source=AnswerSource.KNOWLEDGE_BASE,
        citations=[Citation(title="Stored question", purpose="evidence")],
        confidence=0.9,
        retrieval_latency_ms=1,
        trace_id="trace-session-test",
        domain=TutorDomain.MATH,
        routing_reason="Test route",
    ))
    with TestClient(main.app) as client:
        yield client, selected, TestSession
    main.app.dependency_overrides.clear()
    db.close()


class TestSessionOwnership:
    def test_create_list_and_get_are_scoped_to_current_user(self, session_client):
        client, selected, _ = session_client
        created = client.post("/sessions", json={"title": "Linear algebra"})
        assert created.status_code == 201
        session_id = created.json()["id"]
        assert [item["id"] for item in client.get("/sessions").json()] == [session_id]
        assert client.get(f"/sessions/{session_id}").status_code == 200

        selected["user"] = User(id="user-b", email="b@example.com")
        assert client.get("/sessions").json() == []
        assert client.get(f"/sessions/{session_id}").status_code == 404
        assert client.delete(f"/sessions/{session_id}").status_code == 404

    def test_owner_can_delete_session_and_messages(self, session_client):
        client, _, TestSession = session_client
        session_id = client.post("/sessions", json={"title": "Temporary"}).json()["id"]
        client.post("/chat", json={"message": "Solve x", "session_id": session_id})
        assert client.delete(f"/sessions/{session_id}").status_code == 204
        assert client.get(f"/sessions/{session_id}").status_code == 404
        with TestSession() as db:
            assert db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count() == 0


class TestSessionChatFlow:
    def test_chat_without_session_creates_one_and_persists_exchange(self, session_client):
        client, _, _ = session_client
        response = client.post("/chat", json={"message": "Teach me vectors"})
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        detail = client.get(f"/sessions/{session_id}").json()
        assert detail["title"] == "Teach me vectors"
        assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
        assert detail["messages"][1]["trace_id"] == "trace-session-test"
        assert detail["messages"][1]["route"] == "rag"

    def test_subsequent_chat_appends_to_owned_session(self, session_client):
        client, _, _ = session_client
        session_id = client.post("/chat", json={"message": "First"}).json()["session_id"]
        response = client.post("/chat", json={"message": "Second", "session_id": session_id})
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id
        messages = client.get(f"/sessions/{session_id}").json()["messages"]
        assert [item["content"] for item in messages] == [
            "First", "Tutor response to: First", "Second", "Tutor response to: Second"
        ]

    def test_chat_cannot_write_to_another_users_session(self, session_client):
        client, selected, _ = session_client
        session_id = client.post("/sessions", json={"title": "Private"}).json()["id"]
        selected["user"] = User(id="user-b", email="b@example.com")
        response = client.post("/chat", json={"message": "Intrusion", "session_id": session_id})
        assert response.status_code == 404

    def test_history_reads_are_bounded_to_100_messages(self, session_client):
        _, _, TestSession = session_client
        with TestSession() as db:
            session = SessionService.create(db, "user-a", "Long session")
            db.add_all([
                ChatMessage(
                    id=f"message-{index:03d}", session_id=session.id,
                    role="user", content=str(index)
                )
                for index in range(120)
            ])
            db.commit()
            messages = SessionService.recent_messages(db, session.id, limit=10_000)
            assert len(messages) == 100
            assert messages[0].content == "20"
            assert messages[-1].content == "119"
