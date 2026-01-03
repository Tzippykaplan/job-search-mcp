import pytest

from job_mcp.services.extract_job_requirements_service import JobRequirementsExtractionService
from job_mcp.exceptions import ValidationError


class FakeLLM:
    """
    Fake for the NEW LLM interface used by JobRequirementsExtractionService:
    it must expose: async generate_text(prompt: str) -> str
    """
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.last_prompt: str | None = None

    async def generate_text(self, prompt: str) -> str:
        self.calls.append(prompt)
        self.last_prompt = prompt

        # Return valid JSON (the service robust_json_loads/json parsing expects this)
        return """
        {
          "title": "Title From HTML",
          "company": "TestCorp",
          "location": null,
          "years_experience": ["2 years"],
          "must_have_tech": ["Python", "SQL"],
          "nice_to_have_tech": [],
          "soft_skills": [],
          "notes": []
        }
        """


@pytest.mark.asyncio
async def test_extract_raises_when_no_input():
    service = JobRequirementsExtractionService(llm=FakeLLM())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        await service.extract_job_requirements()


@pytest.mark.asyncio
async def test_extract_with_job_url_uses_fetcher_and_passes_title_hint():
    llm = FakeLLM()

    async def fake_fetcher(url: str):
        assert url == "https://example.com/job"
        return ("Title From HTML", "Requirements: Python, SQL. Must have 2 years.")

    service = JobRequirementsExtractionService(llm=llm, job_page_fetcher=fake_fetcher)  # type: ignore[arg-type]

    result = await service.extract_job_requirements(job_url="https://example.com/job")

    assert result["source"] == "job_url"
    assert result["job_url"] == "https://example.com/job"

    assert "extracted" in result
    assert result["extracted"]["title"] == "Title From HTML"  # from our fake JSON

    # Ensure LLM was called once and title_hint made it into the prompt
    assert len(llm.calls) == 1
    assert llm.last_prompt is not None
    assert "title_hint: Title From HTML" in llm.last_prompt


@pytest.mark.asyncio
async def test_extract_blocked_when_fetcher_returns_empty_and_llm_not_called():
    llm = FakeLLM()

    async def fake_fetcher(url: str):
        return (None, "")

    service = JobRequirementsExtractionService(llm=llm, job_page_fetcher=fake_fetcher)  # type: ignore[arg-type]

    result = await service.extract_job_requirements(job_url="https://blocked.com")

    assert result["error"] == "blocked_by_site"
    assert "message" in result
    assert llm.calls == []
