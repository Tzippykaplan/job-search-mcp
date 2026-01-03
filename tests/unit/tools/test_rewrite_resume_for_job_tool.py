from __future__ import annotations

import pytest
import job_mcp.tools.rewrite_resume_for_job_tool as tool_mod


class FakeService:
    def __init__(self) -> None:
        self.calls = []
        self.result = {"ok": True, "rewritten_resume": "FINAL"}

    async def rewrite_resume_for_job(self, *, job_requirements, match_result, resume_text=None, resume_file_path=None):
        self.calls.append((job_requirements, match_result, resume_text, resume_file_path))
        return self.result


@pytest.mark.asyncio
async def test_rewrite_resume_for_job_tool_forwards_params(monkeypatch):
    fake = FakeService()
    monkeypatch.setattr(tool_mod, "RewriteResumeService", lambda: fake)

    job_requirements = {"extracted": {"title": "Backend"}}
    match_result = {"score": 80}

    out = await tool_mod.rewrite_resume_for_job_tool(
        job_requirements=job_requirements,
        match_result=match_result,
        resume_text="resume",
        resume_file_path=None,
    )

    assert out == fake.result
    assert fake.calls == [(job_requirements, match_result, "resume", None)]
