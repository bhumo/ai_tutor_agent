"""Phase-two request-size, rate, and concurrency protection tests."""

from types import SimpleNamespace

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

import auth.routes as auth_routes
import main
from auth.routes import get_current_user
from database.models import Base, User, get_db
from utils.rate_limit import ConcurrencyLimiter, ConcurrencyLimitExceeded, SlidingWindowRateLimiter


class MutableClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TestSlidingWindowLimiter:
    def test_limit_boundary_and_retry_after(self):
        clock = MutableClock()
        limiter = SlidingWindowRateLimiter(clock)
        assert limiter.check("user", 2, 60).allowed
        assert limiter.check("user", 2, 60).allowed
        denied = limiter.check("user", 2, 60)
        assert denied.allowed is False
        assert denied.retry_after == 60

    def test_window_expiry_restores_capacity(self):
        clock = MutableClock()
        limiter = SlidingWindowRateLimiter(clock)
        assert limiter.check("user", 1, 10).allowed
        clock.now = 10
        assert limiter.check("user", 1, 10).allowed

    def test_users_have_independent_buckets(self):
        limiter = SlidingWindowRateLimiter(lambda: 0)
        assert limiter.check("user-a", 1, 60).allowed
        assert limiter.check("user-b", 1, 60).allowed
        assert limiter.check("user-a", 1, 60).allowed is False


class TestConcurrencyLimiter:
    def test_limit_is_enforced_and_released(self):
        limiter = ConcurrencyLimiter()
        with limiter.acquire("user", 1):
            assert limiter.active("user") == 1
            with pytest.raises(ConcurrencyLimitExceeded):
                with limiter.acquire("user", 1):
                    pass
        assert limiter.active("user") == 0

    def test_exception_does_not_leak_slot(self):
        limiter = ConcurrencyLimiter()
        with pytest.raises(RuntimeError):
            with limiter.acquire("user", 1):
                raise RuntimeError("boom")
        with limiter.acquire("user", 1):
            assert limiter.active("user") == 1


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase2.db'}", connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    user = User(id="phase-two-user", email="phase2@example.com", hashed_password="unused")
    with TestSession() as db:
        db.add(user)
        db.commit()

    def override_db():
        with TestSession() as db:
            yield db

    main.chat_rate_limiter.clear()
    auth_routes.auth_rate_limiter.clear()
    main.app.dependency_overrides[get_db] = override_db
    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="phase-two-user", email="phase2@example.com", full_name="Phase Two"
    )
    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    engine.dispose()


class TestHttpProtections:
    def test_oversized_body_is_rejected_before_json_parsing(self, client):
        response = client.post(
            "/chat",
            content=b"x" * 16_385,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
        assert response.json() == {"detail": "Request body is too large"}

    def test_message_over_4000_characters_is_rejected(self, client):
        response = client.post("/chat", json={"message": "x" * 4_001})
        assert response.status_code == 422

    def test_whitespace_only_message_is_rejected(self, client):
        response = client.post("/chat", json={"message": "   \n"})
        assert response.status_code == 422

    def test_chat_limit_returns_429_and_retry_after(self, client, monkeypatch):
        monkeypatch.setattr(main, "CHAT_RATE_LIMIT", 1)
        monkeypatch.setattr(main.workflow, "process", lambda message: SimpleNamespace(
            answer="ok",
            model_dump=lambda mode: {"route": "rag"},
        ))
        assert client.post("/chat", json={"message": "first"}).status_code == 200
        response = client.post("/chat", json={"message": "second"})
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1

    def test_login_limit_keys_on_ip_and_email(self, client, monkeypatch):
        monkeypatch.setattr(auth_routes, "LOGIN_LIMIT", 1)
        first = client.post("/auth/login", json={
            "email": "missing@example.com", "password": "wrong-password"
        })
        second = client.post("/auth/login", json={
            "email": "missing@example.com", "password": "wrong-password"
        })
        other_email = client.post("/auth/login", json={
            "email": "other@example.com", "password": "wrong-password"
        })
        assert first.status_code == 401
        assert second.status_code == 429
        assert int(second.headers["retry-after"]) >= 1
        assert other_email.status_code == 401
