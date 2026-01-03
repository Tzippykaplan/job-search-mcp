import re
from datetime import datetime
from pathlib import Path

import pytest
from docx import Document

import job_mcp.utils.export_resume_docx as mod
from job_mcp.utils.export_resume_docx import export_resume_to_docx, _safe_filename
from job_mcp.exceptions import ValidationError


def test_safe_filename_default_when_empty():
    assert _safe_filename("") == "resume"
    assert _safe_filename("   ") == "resume"
    assert _safe_filename(None) == "resume"


def test_safe_filename_removes_illegal_chars_and_collapses_spaces():
    name = 'My<>:"/\\|?*\n\tResume   2026'
    out = _safe_filename(name)
    assert "<" not in out and ">" not in out
    assert ":" not in out and "/" not in out and "\\" not in out
    assert "\n" not in out and "\t" not in out
    assert "  " not in out  # no double spaces
    assert out.startswith("My Resume 2026")


def test_safe_filename_truncates_to_120_chars():
    name = "a" * 1000
    out = _safe_filename(name)
    assert len(out) == 120


def test_export_resume_to_docx_raises_on_empty_text(tmp_path):
    with pytest.raises(ValidationError, match="resume_text cannot be empty"):
        export_resume_to_docx("", output_dir=str(tmp_path))


def test_export_resume_to_docx_creates_docx_and_returns_absolute_path(tmp_path):
    out_dir = tmp_path / "out"
    path = export_resume_to_docx("Line1\nLine2", output_dir=str(out_dir), file_name="my_resume", add_timestamp=False)

    p = Path(path)
    assert p.is_absolute()
    assert p.exists()
    assert p.suffix.lower() == ".docx"
    assert p.name == "my_resume.docx"


def test_export_resume_to_docx_writes_paragraphs_preserving_blank_lines(tmp_path):
    out_dir = tmp_path / "out"
    path = export_resume_to_docx("A\n\nB", output_dir=str(out_dir), file_name="x", add_timestamp=False)

    doc = Document(path)
    texts = [p.text for p in doc.paragraphs]
    assert texts == ["A", "", "B"]


def test_export_resume_to_docx_adds_timestamp_when_enabled(tmp_path, monkeypatch):
    fixed = datetime(2026, 1, 1, 12, 34, 56)

    class FakeDateTime:
        @staticmethod
        def now():
            return fixed

    monkeypatch.setattr(mod, "datetime", FakeDateTime)

    out_dir = tmp_path / "out"
    path = export_resume_to_docx("X", output_dir=str(out_dir), file_name="resume", add_timestamp=True)

    assert Path(path).exists()
    assert re.match(r"^resume_20260101_123456\.docx$", Path(path).name)
