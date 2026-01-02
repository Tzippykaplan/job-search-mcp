import pytest
import httpx


from job_mcp.adapters.job_fetcher_httpx import fetch_job_page, extract_title_from_html, html_to_text, focus_on_requirements   


def test_extract_title_prefers_og_title():
    html = """
    <html>
      <head>
        <meta property="og:title" content="  OG Title  " />
        <title>HTML Title</title>
      </head>
    </html>
    """
    assert extract_title_from_html(html) == "OG Title"


def test_extract_title_falls_back_to_title_tag():
    html = "<html><head><title>  My Title </title></head></html>"
    assert extract_title_from_html(html) == "My Title"


def test_extract_title_returns_none_when_missing():
    html = "<html><body>No title</body></html>"
    assert extract_title_from_html(html) is None


def test_html_to_text_removes_unwanted_tags():
    html = """
    <html>
      <head>
        <style>.x{}</style>
        <script>alert(1)</script>
      </head>
      <body>
        <header>HEADER</header>
        <nav>NAV</nav>
        <noscript>NO</noscript>
        <main>
          <h1>Hello</h1>
          <p>World</p>
        </main>
        <footer>FOOT</footer>
      </body>
    </html>
    """
    out = html_to_text(html)

    assert "HEADER" not in out
    assert "NAV" not in out
    assert "NO" not in out
    assert "FOOT" not in out
    assert "alert" not in out
    assert "Hello" in out
    assert "World" in out


def test_html_to_text_collapses_excess_newlines():
    html = "<html><body><p>A</p><p>B</p><p>C</p></body></html>"
    out = html_to_text(html)

    assert "\n\n\n" not in out
    assert "A" in out and "B" in out and "C" in out


def test_focus_on_requirements_extracts_relevant_section():
    text = (
        "Intro " * 300 +
        "Requirements:\n- Python\n- SQL\n" +
        "Footer " * 300
    )

    out = focus_on_requirements(text)

    assert "Requirements" in out or "requirements" in out
    assert len(out) < len(text)  # focused slice


def test_focus_on_requirements_returns_original_when_no_match():
    text = "This is a general description with no keywords."
    assert focus_on_requirements(text) == text


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 403:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(self.status_code),
            )


class FakeAsyncClient:
    def __init__(self, *_, **__):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_fetch_job_page_403_returns_none_and_empty(monkeypatch):
    async def fake_get(self, url, headers=None):
        return FakeResponse(403, "<html></html>")

    monkeypatch.setattr(FakeAsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    title, text = await fetch_job_page("https://blocked.example")

    assert title is None
    assert text == ""


@pytest.mark.asyncio
async def test_fetch_job_page_success(monkeypatch):
    html = """
    <html>
      <head><title>Job Title</title></head>
      <body><p>Requirements: Python</p></body>
    </html>
    """

    async def fake_get(self, url, headers=None):
        return FakeResponse(200, html)

    monkeypatch.setattr(FakeAsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    title, text = await fetch_job_page("https://ok.example")

    assert title == "Job Title"
    assert "Requirements" in text


@pytest.mark.asyncio
async def test_fetch_job_page_non_403_error_raises(monkeypatch):
    async def fake_get(self, url, headers=None):
        return FakeResponse(500, "boom")

    monkeypatch.setattr(FakeAsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_job_page("https://error.example")