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

    async def match_resume_to_job_requirements(self, job_requirements, resume_text):
        self.calls.append((job_requirements, resume_text))
        return self.result


@pytest.mark.asyncio
async def test_match_resume_to_job_calls_service(monkeypatch):
    fake = FakeService()

    # Mock the service class to return our fake
    monkeypatch.setattr(tool_mod, "MatchResumeService", lambda: fake)

    job = {"must_have_tech": ["Python"]}
    resume = "I have Python experience."

    out = await tool_mod.match_resume_to_job(job, resume)

    assert out == fake.result
    assert fake.calls == [(job, resume)]
