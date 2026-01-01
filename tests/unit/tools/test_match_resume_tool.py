from __future__ import annotations

import pytest
import job_mcp.tools.match_resume_to_job_tool as tool_mod


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, str]] = []
        self.result = {
            "score": 80,
            "matched_keywords": ["Python"],
            "missing_keywords": [],
            "strengths": ["Strong backend"],
            "gaps": [],
        }

    async def match(self, job_extracted, resume_text):
        self.calls.append((job_extracted, resume_text))
        return self.result


@pytest.mark.asyncio
async def test_match_resume_to_job_uses_singleton_service_and_calls_match(monkeypatch):
    fake = FakeService()

    # reset module singleton
    tool_mod._service = None

    # make _get_service return our fake
    monkeypatch.setattr(tool_mod, "_get_service", lambda: fake)

    job = {"must_have_tech": ["Python"]}
    resume = "I have Python experience."

    out = await tool_mod.match_resume_to_job(job, resume)

    assert out == fake.result
    assert fake.calls == [(job, resume)]


def test_get_service_creates_singleton(monkeypatch):
    # reset module singleton
    tool_mod._service = None

    created = []

    class FakeMatchResumeService:
        def __init__(self):
            created.append("x")

    # patch the constructor used inside _get_service
    monkeypatch.setattr(tool_mod, "MatchResumeService", FakeMatchResumeService)

    s1 = tool_mod._get_service()
    s2 = tool_mod._get_service()

    assert s1 is s2
    assert len(created) == 1


def test_get_service_returns_existing_singleton():
    sentinel = object()
    tool_mod._service = sentinel  # type: ignore[assignment]

    s = tool_mod._get_service()
    assert s is sentinel
