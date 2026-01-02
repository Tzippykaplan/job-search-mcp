import pytest

from job_mcp.adapters.gemini_client import GeminiLLMClient
import job_mcp.adapters.gemini_client as mod

class FakeModels:
    def __init__(self):
        self.called = None

    def generate_content(self, *, model, contents):
        self.called = {"model": model, "contents": contents}
        # return an object with .text
        return type("Resp", (), {"text": "```json\nhello\n```"})()


class FakeGenaiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.models = FakeModels()


@pytest.mark.asyncio
async def test_gemini_client_generate_text_calls_models_and_strips_fences(monkeypatch):
    # patch env key so init works
    monkeypatch.setenv("GEMINI_API_KEY", "x")

    # patch genai.Client and strip_fences
    monkeypatch.setattr(mod.genai, "Client", FakeGenaiClient)
    monkeypatch.setattr(mod, "strip_fences", lambda t: t.replace("```json", "").replace("```", "").strip())

    # patch asyncio.to_thread so we don't spawn threads in tests
    async def fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(mod.asyncio, "to_thread", fake_to_thread)

    client = GeminiLLMClient()
    out = await client.generate_text("PROMPT", model="some-model")

    assert out == "hello"
    assert client._client.models.called == {"model": "some-model", "contents": "PROMPT"}


def test_gemini_client_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Missing GEMINI_API_KEY"):
        GeminiLLMClient()
