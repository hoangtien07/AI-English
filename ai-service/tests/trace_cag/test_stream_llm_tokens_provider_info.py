from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

import api.services.trace_cag.generate as generate


class _FakeStreamResponse:
    def __init__(self, status_code: int, lines: list[str]) -> None:
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeStreamCtx:
    """Stands in for `httpx.AsyncClient.stream(...)`'s async context manager."""

    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc):
        return False


class _FakeHttpxClient:
    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response
        self.stream_calls: list[tuple[tuple, dict]] = []

    def stream(self, *args, **kwargs):
        self.stream_calls.append((args, kwargs))
        return _FakeStreamCtx(self._response)


class _FakeJsonResponse:
    status_code = 200

    @staticmethod
    def json() -> dict:
        return {
            "candidates": [
                {"content": {"parts": [{"text": "Configured Gemini response"}]}}
            ]
        }


def _groq_sse(*deltas: str) -> list[str]:
    lines = [
        f"data: {json.dumps({'choices': [{'delta': {'content': d}}]})}"
        for d in deltas
    ]
    lines.append("data: [DONE]")
    return lines


def _gemini_sse(*texts: str) -> list[str]:
    return [
        f"data: {json.dumps({'candidates': [{'content': {'parts': [{'text': t}]}}]})}"
        for t in texts
    ]


@pytest.mark.asyncio
async def test_provider_info_reports_groq_when_groq_serves_tokens(monkeypatch):
    monkeypatch.setattr(generate, "_provider_is_disabled", lambda name: False)
    monkeypatch.setattr(
        "api.core.groq_key_pool.try_acquire_groq_key", AsyncMock(return_value="fake-groq-key")
    )
    monkeypatch.setattr("api.core.groq_key_pool.release_groq_key", AsyncMock())
    monkeypatch.setattr("api.core.groq_key_pool.record_groq_key_usage", AsyncMock())
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")
    fake_response = _FakeStreamResponse(200, _groq_sse("Hello", " world"))
    monkeypatch.setattr(
        generate, "_get_httpx_client", lambda name: _FakeHttpxClient(fake_response)
    )

    provider_info: dict = {}
    tokens = [
        token
        async for token in generate.stream_llm_tokens(
            system_prompt="sys",
            messages=[],
            user_input="hi",
            provider_info=provider_info,
        )
    ]

    assert "".join(tokens) == "Hello world"
    assert provider_info == {"provider": "groq", "model": "llama-3.1-8b-instant"}


@pytest.mark.asyncio
async def test_provider_info_reports_gemini_when_groq_yields_nothing(monkeypatch):
    """Groq admitted the key but its stream returned zero tokens (e.g. a
    non-200 status) — the turn must fall back to Gemini, and provider_info
    must reflect Gemini, not silently keep pointing at Groq."""
    monkeypatch.setattr(generate, "_provider_is_disabled", lambda name: False)
    monkeypatch.setattr(
        "api.core.groq_key_pool.try_acquire_groq_key", AsyncMock(return_value="fake-groq-key")
    )
    monkeypatch.setattr("api.core.groq_key_pool.release_groq_key", AsyncMock())
    monkeypatch.setattr("api.core.groq_key_pool.record_groq_key_usage", AsyncMock())
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "models/gemini-env-test")

    groq_failure_response = _FakeStreamResponse(500, [])
    gemini_response = _FakeStreamResponse(200, _gemini_sse("Xin ", "chào"))
    groq_client = _FakeHttpxClient(groq_failure_response)
    gemini_client = _FakeHttpxClient(gemini_response)

    def _fake_client(name: str):
        return groq_client if name == "groq" else gemini_client

    monkeypatch.setattr(generate, "_get_httpx_client", _fake_client)

    provider_info: dict = {}
    tokens = [
        token
        async for token in generate.stream_llm_tokens(
            system_prompt="sys",
            messages=[],
            user_input="hi",
            provider_info=provider_info,
        )
    ]

    assert "".join(tokens) == "Xin chào"
    assert provider_info == {"provider": "gemini", "model": "gemini-env-test"}
    assert gemini_client.stream_calls[0][0][1] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-env-test:streamGenerateContent?alt=sse"
    )


@pytest.mark.asyncio
async def test_generate_node_uses_configured_gemini_url_and_model_metadata(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "models/gemini-env-test")
    monkeypatch.setenv("TRACECAG_ENABLE_LOCAL_LLAMA_KV", "false")
    monkeypatch.setattr(
        "api.core.groq_key_pool.get_available_groq_key",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(generate, "_update_ranker_from_generation", lambda **kwargs: None)
    requests: list[dict] = []

    async def _fake_post_json(**kwargs):
        requests.append(kwargs)
        return _FakeJsonResponse()

    monkeypatch.setattr(generate, "_throttled_post_json", _fake_post_json)

    result = await generate.generate_node(
        {
            "user_input": "Help me practice English.",
            "session_id": "session-gemini-model",
            "learner_profile": {"level": "B1"},
            "conversation_history": [],
            "diagnosis_errors": [],
            "diagnosis_intent": "correct",
            "retrieved_context": "",
            "retrieval_trace": [],
            "grammar_score": 0.8,
            "fluency_score": 0.8,
            "vocabulary_level": "B1",
            "cache_policy": "off",
        }
    )

    assert result["tutor_response"] == "Configured Gemini response"
    assert result["models_used"] == ["gemini-env-test"]
    assert len(requests) == 1
    assert requests[0]["provider"] == "gemini"
    assert requests[0]["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-env-test:generateContent"
    )
