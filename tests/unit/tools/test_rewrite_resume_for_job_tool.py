from __future__ import annotations

import pytest
import job_mcp.tools.rewrite_resume_for_job_tool as tool_mod


class FakeService:
    def __init__(self) -> None:
        self.calls = []
        self.result = {"ok": True, "rewritten_resume": "FINAL"}

    async def rewrite(self, *, job_extracted, match_result, resume_text=None, resume_file_path=None):
        self.calls.append((job_extracted, match_result, resume_text, resume_file_path))
        return self.result


@pytest.mark.asyncio
async def test_rewrite_resume_for_job_tool_forwards_params(monkeypatch):
    tool_mod._service = None
    fake = FakeService()
    monkeypatch.setattr(tool_mod, "_get_service", lambda: fake)

    job_extracted = {"extracted": {"title": "Backend"}}
    match_result = {"score": 80}

    out = await tool_mod.rewrite_resume_for_job_tool(
        job_extracted=job_extracted,
        match_result=match_result,
        resume_text="resume",
        resume_file_path=None,
    )

    assert out == fake.result
    assert fake.calls == [(job_extracted, match_result, "resume", None)]


def test_get_service_is_singleton(monkeypatch):
    tool_mod._service = None
    created = []

    class FakeRewriteResumeService:
        def __init__(self):
            created.append(1)

    monkeypatch.setattr(tool_mod, "RewriteResumeService", FakeRewriteResumeService)

    s1 = tool_mod._get_service()
    s2 = tool_mod._get_service()

    assert s1 is s2
    assert len(created) == 1
