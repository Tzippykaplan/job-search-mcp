from __future__ import annotations

import pytest
import job_mcp.tools.export_resume_docx_tool as tool_mod


class FakeService:
    def __init__(self) -> None:
        self.calls = []
        self.result = {
            "saved_path": "saved.docx",
            "file_name": "name",
            "output_dir": "out",
            "add_timestamp": True,
        }

    async def export(self, *, resume_text: str, output_dir: str, file_name: str | None, add_timestamp: bool):
        self.calls.append((resume_text, output_dir, file_name, add_timestamp))
        return self.result


@pytest.mark.asyncio
async def test_export_resume_docx_tool_forwards_params(monkeypatch):
    tool_mod._service = None
    fake = FakeService()
    monkeypatch.setattr(tool_mod, "_get_service", lambda: fake)

    out = await tool_mod.export_resume_docx_tool(
        rewritten_resume="TEXT",
        output_dir="output_resumes",
        file_name="cv",
        add_timestamp=False,
    )

    assert out == fake.result
    assert fake.calls == [("TEXT", "output_resumes", "cv", False)]


def test_get_service_is_singleton(monkeypatch):
    tool_mod._service = None
    created = []

    class FakeExportResumeDocxService:
        def __init__(self):
            created.append(1)

    monkeypatch.setattr(tool_mod, "ExportResumeDocxService", FakeExportResumeDocxService)

    s1 = tool_mod._get_service()
    s2 = tool_mod._get_service()

    assert s1 is s2
    assert len(created) == 1
