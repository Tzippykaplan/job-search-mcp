import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from job_mcp.tools import extract_job_requirements_tool

class DummyService:
    def __init__(self):
        self.called = False
        self.last_args = None
    async def extract(self, job_url=None, job_text=None):
        self.called = True
        self.last_args = (job_url, job_text)
        return {"ok": True, "job_url": job_url, "job_text": job_text}

@pytest.mark.asyncio
async def test_extract_job_requirements_delegates_to_service():
    dummy = DummyService()
    with patch.object(extract_job_requirements_tool, "_get_service", return_value=dummy):
        result = await extract_job_requirements_tool.extract_job_requirements(job_url="url", job_text="text")
        assert dummy.called
        assert dummy.last_args == ("url", "text")
        assert result["ok"] is True
        assert result["job_url"] == "url"
        assert result["job_text"] == "text"

@pytest.mark.asyncio
async def test_extract_job_requirements_raises_on_no_input():
    dummy = DummyService()
    async def raise_value_error(*a, **kw):
        raise ValueError("Provide either job_url or job_text")
    dummy.extract = raise_value_error
    with patch.object(extract_job_requirements_tool, "_get_service", return_value=dummy):
        with pytest.raises(ValueError):
            await extract_job_requirements_tool.extract_job_requirements()
