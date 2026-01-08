# Job Search MCP Server

A **Model Context Protocol (MCP)** server that enables AI agents to autonomously tailor resumes for job applications. Using Google's Gemini AI, it extracts job requirements, scores candidate fit, and rewrites resumes to match -- while enforcing truthfulness constraints that prevent fabricated experience.

## Overview

Built for **MCP-compatible agents** (Claude Desktop, Codex CLI) to orchestrate multi-step job application workflows. Agents receive a job URL, fetch requirements, request the user's resume, analyze gaps, and generate ATS-optimized DOCX output -- all without manual tool chaining.

**This project demonstrates production-grade MCP server design:** layered architecture (tools -> services -> adapters), comprehensive logging and observability, custom exception handling, dependency injection for testability, and prompt engineering that enforces ethical AI constraints.

### Core Capabilities

- **Job Parsing** - Extract structured requirements from job URLs or text (tech stack, experience, soft skills)
- **Resume Matching** - Score resume fit and identify strengths, gaps, and missing keywords
- **Resume Optimization** - Rewrite resumes to emphasize relevant experience while staying truthful
- **DOCX Export** - Generate professional Word documents ready for ATS systems

### How It Works

- Provide a job URL (or paste the job text)
- Tool extracts structured requirements
- Tool asks for your resume (text or file)
- Tool scores fit and identifies gaps
- Tool rewrites the resume (truthful, ATS-friendly)
- Optional: agent exports a `.docx`

### Example Usage

Write to your agent (Claude Desktop, Codex CLI, etc): "I found this job (paste a URL). This is my resume. Can you rewrite it for me?"
The agent will manage the tool chain and return an output.
You can also call a single tool. For example: "What are my chances to get this job?"
The agent will call `match_resume_to_job` and return the score and gaps.

```text
Job URL: https://www.example.com/job
Here is my resume text (shortened): ...
Please analyze the requirements, tailor my resume, and export a DOCX.
```

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Google Gemini API key** - [Get one here](https://ai.google.dev/)

### Installation

```bash
git clone https://github.com/Tzippykaplan/job-search-mcp/
cd job-search-mcp

# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install package
pip install -e .

# For development (includes pytest, black, ruff)
pip install -e ".[dev]"
```

**Dependencies:**
- `beautifulsoup4` - HTML parsing for job pages
- `google-genai` - Google Gemini AI SDK
- `httpx` - Async HTTP client with SSL support
- `mcp[cli]` - Model Context Protocol framework
- `python-docx` - DOCX file generation
- `python-dotenv` - Environment variable management
- `truststore` - System SSL certificate integration

### Configuration

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
```

**Logging:**
- Console: INFO and above (real-time output)
- File: `logs/mcp-server.log` (DEBUG and above, 10MB rotation)
---

## Agent Integration

### Claude Desktop (Recommended)

Add to your Claude Desktop MCP config file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "job-search-mcp": {
      "command": "C:/Users/YourName/path/job-search-mcp/.venv/Scripts/python.exe",
      "args": ["-u", "C:/Users/YourName/path/job-search-mcp/src/job_mcp/server.py"],
      "cwd": "C:/Users/YourName/path/to/job-search-mcp",
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Important Notes:**
- Use **forward slashes (/)** even on Windows
- Use **absolute paths** to your virtual environment Python and server.py
- Replace `YourName` with your actual username
- The server starts automatically when Claude Desktop launches
- Restart Claude Desktop after making changes

### OpenAI Codex CLI

```bash
codex mcp add job-search-mcp -- \
  /path/to/.venv/Scripts/python.exe \
  -u /path/to/src/job_mcp/server.py

codex
```

### Agent Workflow (5-6 steps)

- Provide `job_url` (or paste `job_text` if scraping fails)
- Agent calls `extract_job_requirements` -> gets structured requirements
- Agent asks for your resume (`resume_text` or `resume_file_path`)
- Agent calls `match_resume_to_job` -> gets score + gaps/keywords
- Agent calls `rewrite_resume_for_job` -> produces a tailored, truthful rewrite
- (Optional) Agent calls `export_resume_docx` -> returns `saved_path` for the generated `.docx`

### Short Usage Example (No Long Outputs)

- Keep the prompt short; avoid pasting long outputs back into chat.

---

## Architecture

### Tool Pipeline

The four MCP tools work together in a sequential pipeline:

```
extract_job_requirements -> match_resume_to_job -> rewrite_resume_for_job -> export_resume_docx
```

**1. Extract Job Requirements**
   - Input: `job_url` or `job_text`
   - Output: Structured requirements (tech stack, experience, soft skills)

**2. Match Resume to Job**
   - Input: Job requirements + resume text
   - Output: Match score (0-100), strengths, gaps, keywords

**3. Rewrite Resume**
   - Input: Job requirements + match result + resume
   - Output: Optimized resume with sections and change log

**4. Export to DOCX**
   - Input: Rewritten resume text
   - Output: Professional `.docx` file path

### Project Structure

```
src/job_mcp/
|_ server.py              # MCP server entry point
|_ config.py              # Configuration (model, limits, paths)
|_ exceptions.py          # Custom exception hierarchy
|_ tools/                 # MCP tool wrappers
|  |_ extract_job_requirements_tool.py
|  |_ match_resume_to_job_tool.py
|  |_ rewrite_resume_for_job_tool.py
|  |_ export_resume_docx_tool.py
|_ services/              # Business logic layer
|  |_ extract_job_requirements_service.py
|  |_ match_resume_to_job_service.py
|  |_ rewrite_resume_for_job_service.py
|  |_ export_resume_docx_service.py
|_ adapters/              # External integrations
|  |_ gemini_client.py        # Gemini AI client
|  |_ job_page_fetcher.py     # Job page scraping (httpx + BeautifulSoup)
|_ utils/                 # Shared utilities
|  |_ gemini_helpers.py       # JSON parsing, fence stripping
|  |_ read_resume.py          # Resume file readers (.txt, .md, .docx)
|  |_ export_resume_docx.py   # DOCX generation
|  |_ validation.py           # Input validation helpers
|  |_ logger.py               # Logging configuration
|_ prompts/               # AI prompt templates
|  |_ system_prompt.txt
```

### Design Principles

- **Layered Architecture**: Tools -> Services -> Adapters -> Utils
- **Dependency Injection**: Services accept mock adapters for testing
- **Custom Exceptions**: Proper error categorization (ValidationError, LLMResponseError, FileReadError)
- **Comprehensive Logging**: Structured logs for debugging and monitoring
- **Input Validation**: All tool parameters validated before processing
- **Truthful AI**: Prompts explicitly forbid inventing experience or skills
- **ATS-friendly**: DOCX output optimized for applicant tracking systems
- **Type Safety**: Full type hints with Python 3.12+ syntax

---

## Configuration

Customize settings in [src/job_mcp/config.py](src/job_mcp/config.py):

| Setting | Default | Description |
|---------|---------|-------------|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini AI model to use |
| `MAX_JOB_TEXT_LENGTH` | `18000` | Max job text characters processed |
| `MAX_RESUME_LENGTH` | `16000` | Max resume characters processed |
| `DEFAULT_OUTPUT_DIR` | `output_resumes` | Default DOCX save location |
| `SUPPORTED_RESUME_FORMATS` | `[.txt, .md, .docx]` | Resume file types accepted |

---

## Development

### Running Tests

```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest tests/unit/        # Unit tests only
python -m pytest -q

```

### Code Quality

```bash
black src/                # Format code
ruff check src/ --fix     # Lint and auto-fix
pyright src/              # Type checking
```

---

## Cost Estimation

Using **Gemini 2.5 Flash** (as of 2026): **~$0.07 per application** (extraction + matching + rewriting). Prices vary by region. Monitor usage in [Google AI Studio](https://ai.google.dev/).

---

## Limitations

- **Scraping**: Some job sites block automated requests (403). Use `job_text` as fallback.
- **Truthfulness**: AI only reshapes existing content -- cannot invent skills or experience.
- **Quality**: Best results require well-formatted input resumes with clear sections.

---

## Troubleshooting

### "Missing GEMINI_API_KEY" Error
- Ensure `.env` file exists in project root with your API key
- For Claude Desktop, add API key to the `env` section in config JSON

### Server Not Appearing in Claude Desktop
- Verify paths use forward slashes (`/`) even on Windows
- Check paths are absolute, not relative
- Restart Claude Desktop after config changes
- Check Claude Desktop logs for error messages

### Tests Failing
```bash
# Clear Python cache and retry
python -m pytest --cache-clear -v

# Or manually clean cache:
# Mac/Linux: find . -type d -name __pycache__ -exec rm -r {} +
# Windows: Get-ChildItem -Recurse __pycache__ | Remove-Item -Recurse -Force
```

### Import Errors
- Ensure you installed with `pip install -e .` from project root
- Verify virtual environment is activated
- Check that all `__init__.py` files exist in package directories

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

---

**Made with ❤️ for anyone looking for their next job.**
