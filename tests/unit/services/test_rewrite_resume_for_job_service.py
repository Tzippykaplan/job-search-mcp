# tests/unit/services/test_rewrite_resume_service.py
from __future__ import annotations

import json
import pytest

from job_mcp.services.rewrite_resume_for_job_service import RewriteResumeService
from job_mcp.exceptions import ValidationError, LLMResponseError


class FakeLLM:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[str] = []
        self.last_prompt: str | None = None

    async def generate_text(self, prompt: str) -> str:
        self.calls.append(prompt)
        self.last_prompt = prompt
        return self.response_text


def fake_reader(path: str) -> str:
    assert path == "resume.pdf"
    return "My Resume\nPython developer\n"


@pytest.mark.asyncio
async def test_rewrite_raises_when_no_resume_text_and_no_file():
    svc = RewriteResumeService(llm=FakeLLM("{}"))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="Provide either resume_text or resume_file_path"):
        await svc.rewrite_resume_for_job(job_requirements={}, match_result={}, resume_text=None, resume_file_path=None)


@pytest.mark.asyncio
async def test_rewrite_reads_from_file_when_resume_file_path_provided():
    llm = FakeLLM(
        json.dumps(
            {
                "sections": {
                    "Summary": "Summary text",
                    "Skills": "Python",
                    "Experience": "",
                    "Projects": "",
                    "Education": "",
                },
                "rewritten_resume": "FULL RESUME",
                "changes": ["Updated summary"],
                "warnings": [],
            }
        )
    )
    svc = RewriteResumeService(llm=llm, resume_reader=fake_reader)  # type: ignore[arg-type]

    out = await svc.rewrite_resume_for_job(
        job_requirements={"title": "Backend"},
        match_result={"score": 70},
        resume_text=None,
        resume_file_path="resume.pdf",
    )

    assert out["rewritten_resume"] == "FULL RESUME"
    assert llm.last_prompt is not None
    assert "ORIGINAL RESUME:" in llm.last_prompt
    assert "My Resume" in llm.last_prompt


@pytest.mark.asyncio
async def test_rewrite_accepts_nested_job_extracted_extracted_key():
    llm = FakeLLM(
        json.dumps(
            {
                "sections": {"Summary": "", "Skills": "", "Experience": "", "Projects": "", "Education": ""},
                "rewritten_resume": "OK",
                "changes": [],
                "warnings": [],
            }
        )
    )
    svc = RewriteResumeService(llm=llm)  # type: ignore[arg-type]

    job_requirements = {"extracted": {"title": "Title A", "must_have_tech": ["Python"]}}
    await svc.rewrite_resume_for_job(job_requirements=job_requirements, match_result={}, resume_text="resume", resume_file_path=None)

    assert llm.last_prompt is not None
    assert '"title": "Title A"' in llm.last_prompt


@pytest.mark.asyncio
async def test_rewrite_builds_prompt_with_filtered_payloads_and_calls_llm_once():
    llm = FakeLLM(
        json.dumps(
            {
                "sections": {"Summary": "S", "Skills": "K", "Experience": "E", "Projects": "", "Education": ""},
                "rewritten_resume": "FINAL",
                "changes": ["x"],
                "warnings": ["y"],
            }
        )
    )
    svc = RewriteResumeService(llm=llm)  # type: ignore[arg-type]

    job_requirements = {
        "title": "Backend Engineer",
        "must_have_tech": ["Python", "Postgres"],
        "nice_to_have_tech": ["Kubernetes"],
        "years_experience": ["2+"],
        "responsibilities": ["Build APIs"],
        "notes": ["Hybrid"],
        "should_not_leak": "SECRET",  # should not appear because filtered_job_requirements filters it out
    }
    match_result = {
        "score": 80,
        "matched_keywords": ["Python"],
        "missing_keywords": ["Kubernetes"],
        "strengths": ["Backend"],
        "gaps": ["No K8s"],
        "other": "IGNORE",
    }

    out = await svc.rewrite_resume_for_job(job_requirements=job_requirements, match_result=match_result, resume_text="R", resume_file_path=None)

    assert out["rewritten_resume"] == "FINAL"
    assert len(llm.calls) == 1
    assert llm.last_prompt is not None
    assert "JOB REQUIREMENTS (FILTERED):" in llm.last_prompt
    assert "MATCH ANALYSIS (FILTERED):" in llm.last_prompt
    assert "ORIGINAL RESUME:" in llm.last_prompt

    # Ensure filtering happened (the SECRET key should not be in prompt)
    assert "should_not_leak" not in llm.last_prompt
    assert "SECRET" not in llm.last_prompt


@pytest.mark.asyncio
async def test_rewrite_invalid_json_from_llm_raises_clean_error():
    llm = FakeLLM("NOT JSON")
    svc = RewriteResumeService(llm=llm)  # type: ignore[arg-type]

    with pytest.raises(LLMResponseError, match="Gemini returned invalid JSON. Could not rewrite resume"):
        await svc.rewrite_resume_for_job(job_requirements={}, match_result={}, resume_text="resume", resume_file_path=None)


@pytest.mark.asyncio
async def test_rewrite_non_object_json_raises():
    llm = FakeLLM('["not", "object"]')
    svc = RewriteResumeService(llm=llm)  # type: ignore[arg-type]

    with pytest.raises(LLMResponseError, match="not an object"):
        await svc.rewrite_resume_for_job(job_requirements={}, match_result={}, resume_text="resume", resume_file_path=None)


@pytest.mark.asyncio
async def test_rewrite_normalize_builds_rewritten_resume_when_missing():
    # rewritten_resume is empty -> service should compose from sections
    llm = FakeLLM(
        json.dumps(
            {
                "sections": {
                    "Summary": "Sum",
                    "Skills": "Skills",
                    "Experience": "",
                    "Projects": "Proj",
                    "Education": "",
                },
                "rewritten_resume": "   ",
                "changes": ["c1", 123, None],
                "warnings": ["w1", {}, "w2"],
            }
        )
    )
    svc = RewriteResumeService(llm=llm)  # type: ignore[arg-type]

    out = await svc.rewrite_resume_for_job(job_requirements={}, match_result={}, resume_text="resume", resume_file_path=None)

    assert "Summary\nSum" in out["rewritten_resume"]
    assert "Skills\nSkills" in out["rewritten_resume"]
    assert "Projects\nProj" in out["rewritten_resume"]
    # as_list should filter non-strings
    assert out["changes"] == ["c1"]
    assert out["warnings"] == ["w1", "w2"]


def test_compact_text_removes_trailing_spaces_and_limits_blank_lines():
    s = "Line 1   \r\n\r\n\r\nLine 2   \n\n\n\nLine 3"
    compact = RewriteResumeService._compact_text(s)
    assert compact == "Line 1\n\nLine 2\n\nLine 3"
