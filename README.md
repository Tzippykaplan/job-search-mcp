# Job Search MCP Server

An intelligent **Model Context Protocol (MCP)** server that automates job application preparation using Google's Gemini AI. Extract job requirements, analyze resume fit, and generate optimized, ATS-friendly resumes—all through a seamless agent-driven workflow.

## Overview

This MCP server bridges job postings and resumes, helping job seekers tailor their applications efficiently. Designed for use with MCP-compatible AI agents (Claude Desktop, Codex CLI), it automates the tedious process of analyzing job requirements and reshaping resumes to match—without inventing experience or skills.

### Core Capabilities

- **Job Parsing** – Extract structured requirements from job URLs or text (tech stack, experience, soft skills)
- **Resume Matching** – Score resume fit and identify strengths, gaps, and missing keywords
- **Resume Optimization** – Rewrite resumes to emphasize relevant experience while staying truthful
- **DOCX Export** – Generate professional Word documents ready for ATS systems

### How It Works

Designed for **autonomous agent workflows**. Simply provide a job posting URL or paste the description—the agent proactively orchestrates the tools, requests your resume when needed, and produces a tailored output. No manual step-by-step configuration required.
---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Google Gemini API key** – [Get one here](https://ai.google.dev/)

### Installation

```bash
git clone <repository-url>
cd job-search-mcp
pip install -e .

# For development
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```
---

## Agent Integration

### Claude Desktop (Recommended)

Add to your Claude Desktop MCP config file:

```json
{
  "mcpServers": {
    "job-search-mcp": {
      "command": "/path/to/job-search-mcp/.venv/Scripts/python.exe",
      "args": ["-u", "/path/to/job-search-mcp/src/job_mcp/server.py"],
      "cwd": "/path/to/job-search-mcp",
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Note:** Use absolute paths. The server starts automatically when Claude Desktop launches.

### OpenAI Codex CLI

```bash
codex mcp add job-search-mcp -- \
  /path/to/.venv/Scripts/python.exe \
  -u /path/to/src/job_mcp/server.py

codex
```

### Example Usage

Once connected to an agent, simply provide natural language instructions:

```text
I want to apply for this job:
https://example.com/software-engineer-role

Analyze the requirements, evaluate my resume, and optimize it for this position.
```

The agent will:
1. Extract job requirements
2. Request your resume (if not provided)
3. Analyze match score and gaps
4. Rewrite and export an optimized DOCX

---

## Architecture

### Tool Pipeline

The four MCP tools work together in a sequential pipeline:

```
extract_job_requirements → match_resume_to_job → rewrite_resume_for_job → export_resume_docx
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
├── exceptions.py 
├── server.py              # MCP server entry point
├── config.py              # Configuration (model, limits, paths)
├── tools/                 # MCP tool wrappers
│   ├── extract_job_requirements_tool.py
│   ├── match_resume_to_job_tool.py
│   ├── rewrite_resume_for_job_tool.py
│   └── export_resume_docx_tool.py
├── services/              # Business logic layer
│   ├── job_requirements_service.py
│   ├── match_resume_service.py
│   ├── rewrite_resume_service.py
│   └── export_resume_docx_service.py
├── adapters/              # External integrations
│   ├── job_fetcher_httpx.py    # Job page scraping
│   └── llm_gemini_client.py    # Gemini AI client
└── utils/                 # Shared utilities
    ├── gemini_helpers.py  # JSON parsing, fence stripping
    ├── read_resume.py     # Resume file readers (.txt, .md, .docx)
    └── export_resume_docx.py  # DOCX generation
```

### Design Principles

- **Clean separation**: Tools → Services → Adapters → Utils
- **Testable**: Each layer is independently testable with mock objects
- **Truthful AI**: Prompts explicitly forbid inventing experience or skills
- **ATS-friendly**: DOCX output optimized for applicant tracking systems

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

Using **Gemini 2.5 Flash** (as of 2026):

- Job extraction: ~1,000 tokens (~$0.01)
- Resume matching: ~2,000 tokens (~$0.02)  
- Resume rewriting: ~4,000 tokens (~$0.04)

**Total per application: ~$0.07**

Prices vary by region and usage tier. Monitor usage in [Google AI Studio](https://ai.google.dev/).

---

## Limitations

- **Scraping**: Some job sites block automated requests (403 errors). Use `job_text` parameter as fallback.
- **Truthfulness**: The AI only reshapes existing content—it cannot invent new skills or experience.
- **Resume Quality**: Best results require well-formatted input resumes with clear sections.

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