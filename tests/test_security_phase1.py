"""Phase-one security boundary and regression tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

from auth.routes import get_current_user
from database.models import Base, User, get_db
from main import app, workflow
from utils.security_config import get_allowed_origins, get_required_secret_key


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase1.db'}", connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    user = User(id="qa-user", email="qa@example.com", hashed_password="unused")
    with TestSession() as db:
        db.add(user)
        db.commit()

    def override_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="qa-user", email="qa@example.com", full_name="QA User"
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


class TestFailClosedConfiguration:
    @pytest.mark.parametrize("value", ["", "short", "your-secret-key", "change-me-please-change-me-please"])
    def test_weak_or_placeholder_secret_is_rejected(self, value):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            get_required_secret_key({"SECRET_KEY": value})

    def test_strong_secret_is_accepted(self):
        secret = "a" * 32
        assert get_required_secret_key({"SECRET_KEY": secret}) == secret

    def test_wildcard_cors_is_rejected(self):
        with pytest.raises(RuntimeError, match="Wildcard"):
            get_allowed_origins({"ALLOWED_ORIGINS": "*"})

    def test_explicit_cors_origins_are_normalized(self):
        assert get_allowed_origins({
            "ALLOWED_ORIGINS": "https://app.example.com/, http://localhost:8000"
        }) == ["https://app.example.com", "http://localhost:8000"]


class TestProtectedChatBoundary:
    def test_public_chat_route_does_not_exist(self, client):
        assert client.post("/chat/public", json={"message": "hello"}).status_code == 404

    def test_empty_message_is_rejected(self, client):
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 422
        assert response.json() == {"detail": "A non-empty message is required"}

    def test_provider_exception_returns_controlled_error(self, client, monkeypatch):
        monkeypatch.setattr(workflow, "process", lambda message: (_ for _ in ()).throw(
            RuntimeError("provider response containing sensitive internals")
        ))
        response = client.post("/chat", json={"message": "Explain vectors"})
        assert response.status_code == 503
        assert response.json() == {
            "detail": "The tutor is temporarily unavailable. Please try again."
        }
        assert "sensitive internals" not in response.text


class TestCorsAndBrowserRendering:
    def test_allowed_origin_receives_cors_header(self, client):
        response = client.options("/chat", headers={
            "Origin": "http://127.0.0.1:8000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8000"

    def test_untrusted_origin_receives_no_cors_permission(self, client):
        response = client.options("/chat", headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        })
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_model_markdown_is_sanitized_before_html_insertion(self):
        frontend = Path("frontend/index.html").read_text(encoding="utf-8")
        assert "DOMPurify.sanitize(marked.parse(data.response))" in frontend
        assert "botMessage.innerHTML = marked.parse(data.response)" not in frontend

    def test_dompurify_is_loaded(self):
        frontend = Path("frontend/index.html").read_text(encoding="utf-8")
        assert "dompurify@" in frontend.lower()
