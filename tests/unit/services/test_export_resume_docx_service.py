from __future__ import annotations

import pytest

from job_mcp.services.export_resume_docx_service import ExportResumeDocxService


@pytest.mark.asyncio
async def test_export_calls_export_resume_to_docx_and_returns_metadata(monkeypatch):
    called = {}

    def fake_export_resume_to_docx(*, resume_text: str, output_dir: str, file_name: str | None, add_timestamp: bool) -> str:
        called["resume_text"] = resume_text
        called["output_dir"] = output_dir
        called["file_name"] = file_name
        called["add_timestamp"] = add_timestamp
        return r"C:\tmp\output_resumes\resume.docx"

    # Patch where it's USED (imported into the service module)
    monkeypatch.setattr(
        "job_mcp.services.export_resume_docx_service.export_resume_to_docx",
        fake_export_resume_to_docx,
    )

    svc = ExportResumeDocxService()
    out = await svc.export(
        resume_text="MY RESUME TEXT",
        output_dir="output_resumes",
        file_name="my_resume",
        add_timestamp=False,
    )

    assert called == {
        "resume_text": "MY RESUME TEXT",
        "output_dir": "output_resumes",
        "file_name": "my_resume",
        "add_timestamp": False,
    }
    assert out == {
        "saved_path": r"C:\tmp\output_resumes\resume.docx",
        "output_dir": "output_resumes",
        "add_timestamp": False,
    }


@pytest.mark.asyncio
async def test_export_uses_defaults(monkeypatch):
    def fake_export_resume_to_docx(*, resume_text: str, output_dir: str, file_name: str | None, add_timestamp: bool) -> str:
        assert resume_text == "TEXT"
        assert output_dir == "output_resumes"
        assert file_name is None
        assert add_timestamp is True
        return "saved.docx"

    monkeypatch.setattr(
        "job_mcp.services.export_resume_docx_service.export_resume_to_docx",
        fake_export_resume_to_docx,
    )

    svc = ExportResumeDocxService()
    out = await svc.export(resume_text="TEXT")

    assert out["saved_path"] == "saved.docx"
    assert out["output_dir"] == "output_resumes"
    assert out["add_timestamp"] is True
