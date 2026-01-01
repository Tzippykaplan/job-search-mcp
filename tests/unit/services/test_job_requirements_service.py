import pytest

from job_mcp.services.job_requirements_service import JobRequirementsService


class FakeLLM:
    def __init__(self) -> None:
        self.calls = []

    def extract_job(self, job_text: str, title_hint: str | None = None):
        self.calls.append((job_text, title_hint))
        return {
            "title": title_hint or "Backend Developer",
            "company": "TestCorp",
        }


@pytest.mark.asyncio
async def test_extract_raises_when_no_input():
    service = JobRequirementsService(llm=FakeLLM())
    with pytest.raises(ValueError):
        await service.extract()


@pytest.mark.asyncio
async def test_extract_with_job_url_uses_fetcher_and_passes_title_hint():
    llm = FakeLLM()

    async def fake_fetcher(url: str):
        assert url == "https://example.com/job"
        return ("Title From HTML", "Requirements: Python, SQL. Must have 2 years.")

    service = JobRequirementsService(llm=llm, fetcher=fake_fetcher)

    result = await service.extract(job_url="https://example.com/job")

    assert result["source"] == "job_url"
    assert result["job_url"] == "https://example.com/job"
    assert result["extracted"]["title"] == "Title From HTML"
    assert llm.calls[0][1] == "Title From HTML"  # title_hint passed


@pytest.mark.asyncio
async def test_extract_blocked_when_fetcher_returns_empty_and_llm_not_called():
    llm = FakeLLM()

    async def fake_fetcher(url: str):
        return (None, "")

    service = JobRequirementsService(llm=llm, fetcher=fake_fetcher)

    result = await service.extract(job_url="https://blocked.com")

    assert result["error"] == "blocked_by_site"
    assert "message" in result
    assert llm.calls == []
