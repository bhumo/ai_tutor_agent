import pytest

import rag.generator as generator_module
import rag.router as router_module
from rag.config import get_gemini_client_options
from rag.generator import GeminiAnswerGenerator
from rag.router import GeminiDomainJudge


class FakeStructuredClient:
    def with_structured_output(self, schema):
        return (schema, self)


class CapturingClient(FakeStructuredClient):
    calls = []

    def __init__(self, **kwargs):
        self.calls.append(kwargs)


def test_provider_defaults_are_bounded():
    assert get_gemini_client_options({}) == {"timeout": 20.0, "max_retries": 2}


@pytest.mark.parametrize(
    "env",
    [
        {"GEMINI_TIMEOUT_SECONDS": "0"},
        {"GEMINI_TIMEOUT_SECONDS": "121"},
        {"GEMINI_MAX_RETRIES": "-1"},
        {"GEMINI_MAX_RETRIES": "6"},
        {"GEMINI_MAX_RETRIES": "many"},
    ],
)
def test_invalid_provider_limits_fail_closed(env):
    with pytest.raises(RuntimeError):
        get_gemini_client_options(env)


def test_router_and_generator_apply_the_same_limits(monkeypatch):
    CapturingClient.calls.clear()
    monkeypatch.setattr(router_module, "ChatGoogleGenerativeAI", CapturingClient)
    monkeypatch.setattr(generator_module, "ChatGoogleGenerativeAI", CapturingClient)
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setenv("GEMINI_MAX_RETRIES", "1")

    GeminiDomainJudge("test-key")
    GeminiAnswerGenerator("test-key")

    assert len(CapturingClient.calls) == 2
    assert all(call["timeout"] == 7.5 for call in CapturingClient.calls)
    assert all(call["max_retries"] == 1 for call in CapturingClient.calls)
