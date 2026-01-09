from __future__ import annotations

import json
import pytest

from job_mcp.services.match_resume_to_job_service import MatchResumeService
from job_mcp.exceptions import ValidationError, LLMResponseError


class FakeGeminiLLMClient:
    """
    Minimal async fake that captures the prompt and returns a preset response.
    Matches the interface used by MatchResumeService: await llm.generate_text(prompt)
    """

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_prompt: str | None = None
        self.calls: int = 0

    async def generate_text(self, prompt: str) -> str:
        self.calls += 1
        self.last_prompt = prompt
        return self.response_text


@pytest.mark.asyncio
async def test_match_happy_path_parses_and_normalizes() -> None:
    llm = FakeGeminiLLMClient(
        json.dumps(
            {
                "score": 87.9,
                "matched_keywords": ["Python", "Django"],
                "missing_keywords": ["Kubernetes"],
                "strengths": ["Strong backend experience"],
                "gaps": ["No K8s mentioned"],
            }
        )
    )
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    job_extracted = {"must_have_tech": ["Python", "Django"], "nice_to_have_tech": ["Kubernetes"]}
    resume_text = "  I worked with Python and Django for 3 years.  "

    result = await svc.match_resume_to_job_requirements(job_extracted, resume_text=resume_text)

    assert llm.calls == 1
    assert llm.last_prompt is not None

    # Output shape
    assert set(result.keys()) == {"score", "matched_keywords", "missing_keywords", "strengths", "gaps"}

    # Normalization: score int 0-100
    assert result["score"] == 87

    # Normalization: lists of strings
    assert result["matched_keywords"] == ["Python", "Django"]
    assert result["missing_keywords"] == ["Kubernetes"]
    assert result["strengths"] == ["Strong backend experience"]
    assert result["gaps"] == ["No K8s mentioned"]


@pytest.mark.asyncio
async def test_match_builds_prompt_includes_job_and_resume_snippet() -> None:
    llm = FakeGeminiLLMClient(
        '{"score": 50, "matched_keywords": [], "missing_keywords": [], "strengths": [], "gaps": []}'
    )
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    job_extracted = {"title": "Backend Engineer", "must_have_tech": ["Python"]}
    resume_text = "Experienced in Python."

    await svc.match_resume_to_job_requirements(job_extracted, resume_text=resume_text)

    assert llm.last_prompt is not None
    prompt = llm.last_prompt

    # Basic prompt invariants
    assert "Return ONLY valid JSON" in prompt
    assert "JOB REQUIREMENTS:" in prompt
    assert "CANDIDATE RESUME:" in prompt

    # Ensure job_extracted JSON got embedded
    assert '"Backend Engineer"' in prompt or "Backend Engineer" in prompt
    assert "Python" in prompt

    # Ensure resume snippet got embedded
    assert "Experienced in Python." in prompt


@pytest.mark.asyncio
async def test_match_raises_on_empty_resume_text() -> None:
    llm = FakeGeminiLLMClient("{}",)
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="Provide either resume_text or resume_file_path"):
        await svc.match_resume_to_job_requirements(job_requirements={"x": 1}, resume_text="   ")

    assert llm.calls == 0


@pytest.mark.asyncio
async def test_match_raises_when_llm_returns_invalid_json() -> None:
    llm = FakeGeminiLLMClient("NOT JSON")
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    with pytest.raises(LLMResponseError, match="Gemini returned invalid JSON for resume matching"):
        await svc.match_resume_to_job_requirements(job_requirements={"x": 1}, resume_text="ok")

    assert llm.calls == 1


@pytest.mark.asyncio
async def test_match_accepts_resume_file_path() -> None:
    llm = FakeGeminiLLMClient(
        '{"score": 75, "matched_keywords": ["Python"], "missing_keywords": [], "strengths": ["Good exp"], "gaps": []}'
    )
    
    def fake_reader(path: str) -> str:
        assert path == "resume.txt"
        return "Python developer with 5 years experience"
    
    svc = MatchResumeService(llm=llm, resume_reader=fake_reader)  # type: ignore[arg-type]

    result = await svc.match_resume_to_job_requirements(
        job_requirements={"must_have_tech": ["Python"]},
        resume_file_path="resume.txt"
    )

    assert result["score"] == 75
    assert llm.calls == 1
    assert "Python developer" in llm.last_prompt


@pytest.mark.asyncio
async def test_match_raises_when_llm_returns_non_object_json() -> None:
    llm = FakeGeminiLLMClient('["not", "an", "object"]')
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    with pytest.raises(LLMResponseError, match="not an object"):
        await svc.match_resume_to_job_requirements(job_requirements={"x": 1}, resume_text="ok")

    assert llm.calls == 1


@pytest.mark.asyncio
async def test_match_normalizes_missing_fields_defaults_and_score_clamps() -> None:
    # Missing arrays + crazy score should get defaults and clamp
    llm = FakeGeminiLLMClient('{"score": 999, "matched_keywords": "Python"}')
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    result = await svc.match_resume_to_job_requirements(job_requirements={"x": 1}, resume_text="ok")

    # score clamp to 100
    assert result["score"] == 100

    # as_list should turn non-list into []
    assert result["matched_keywords"] == []

    # defaults
    assert result["missing_keywords"] == []
    assert result["strengths"] == []
    assert result["gaps"] == []


@pytest.mark.asyncio
async def test_match_normalizes_non_numeric_score_to_zero() -> None:
    llm = FakeGeminiLLMClient(
        '{"score": "high", "matched_keywords": [], "missing_keywords": [], "strengths": [], "gaps": []}'
    )
    svc = MatchResumeService(llm=llm)  # type: ignore[arg-type]

    result = await svc.match_resume_to_job_requirements(job_requirements={"x": 1}, resume_text="ok")
    assert result["score"] == 0
