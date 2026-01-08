#  Job Search MCP Server

<div align="center">

**AI-Powered Resume Tailoring for the Modern Job Search**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---
##  The Problem

You spend hours customizing your resume for each job application. You're never sure if you're highlighting the right skills. ATS systems reject qualified candidates. **It's exhausting.**

##  The Solution

A **Model Context Protocol (MCP)** server that transforms your resume tailoring workflow. Simply provide a job URL and your resume - an AI agent extracts requirements, analyzes your fit, and generates an ATS-optimized resume **in seconds**. All while maintaining complete truthfulness about your experience.

### Why This Matters

-  **10x faster** than manual resume customization
-  **Higher ATS scores** with keyword optimization
-  **Autonomous AI agents** handle the entire workflow
-  **Truthful by design** - never invents fake experience
-  **Professional output** - ready-to-submit DOCX files

---

##  Features

###  Intelligent Job Parsing
- Extract structured requirements from any job posting URL
- Parse tech stacks, experience levels, and soft skills
- Fallback to manual text input for protected sites
- Handles complex, multi-section job descriptions

###  Smart Resume Matching
- 0-100 compatibility scoring
- Identifies your strongest selling points
- Highlights experience gaps and missing keywords
- Provides actionable improvement recommendations

###  AI-Powered Resume Rewriting
- Emphasizes relevant experience for each job
- ATS-optimized keyword placement
- Maintains your authentic voice and truthful content
- Generates detailed change logs for transparency

###  Professional DOCX Export
- Clean, ATS-friendly formatting
- Standard sections (Experience, Skills, Education)
- Compatible with all major ATS systems
- One-click download

---

##  Quick Start

### Prerequisites

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **Google Gemini API Key** ([Get free key](https://ai.google.dev/))
- **MCP-compatible agent** (Claude Desktop, Codex CLI, or custom)

### Installation

```bash
# Clone the repository
git clone https://github.com/Tzippykaplan/job-search-mcp/
cd job-search-mcp

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

# Install the package
pip install -e .

# For development (includes pytest, black, ruff)
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
```

**Logging Configuration:**
- **Console**: INFO and above (real-time feedback)
- **File**: `logs/mcp-server.log` (DEBUG and above, 10MB rotation)

---

##  Agent Integration

### Claude Desktop (Recommended)

1. Open your Claude Desktop MCP config file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the server configuration:

```json
{
  "mcpServers": {
    "job-search-mcp": {
      "command": "C:/Users/YourName/path/to/job-search-mcp/.venv/Scripts/python.exe",
      "args": ["-u", "C:/Users/YourName/path/to/job-search-mcp/src/job_mcp/server.py"],
      "cwd": "C:/Users/YourName/path/to/job-search-mcp",
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

3. **Important Configuration Notes:**
   -  Use **forward slashes (/)** even on Windows
   -  Use **absolute paths** to your virtual environment Python and `server.py`
   -  Replace `YourName` with your actual username
   -  Restart Claude Desktop after making changes

### OpenAI Codex CLI

```bash
codex mcp add job-search-mcp -- \
  /path/to/.venv/Scripts/python.exe \
  -u /path/to/src/job_mcp/server.py
```

---

## Usage

### Simple Workflow

Talk to your AI agent naturally:

```
"I found this job: https://www.example.com/job-posting
Here's my resume: [paste or attach file]
Can you tailor my resume for this position?"
```

The agent will:
1. Extract job requirements
2. Analyze your fit
3. Rewrite your resume
4. Export a professional DOCX

### Advanced Usage

**Single Tool Calls:**

```
"What are my chances for this job?"
→ Calls match_resume_to_job, returns score and gaps

"Extract the requirements from this job posting"
→ Calls extract_job_requirements, returns structured data

"Rewrite my resume for this specific role"
→ Calls rewrite_resume_for_job, returns optimized version
```

### Tool Pipeline

The four MCP tools work sequentially:

```
extract_job_requirements
    ↓
match_resume_to_job
    ↓
rewrite_resume_for_job
    ↓
export_resume_docx
```

---

##  Architecture

### Design Philosophy

This project demonstrates **production-grade MCP server design**:

- **Layered Architecture** - Tools → Services → Adapters → Utils
-  **Dependency Injection** - Services accept mock adapters for testing
-  **Custom Exceptions** - Proper error categorization and handling
- **Comprehensive Logging** - Structured logs for debugging and monitoring
-  **Input Validation** - All parameters validated before processing
-  **Truthful AI** - Prompts explicitly forbid fabricated experience
-  **ATS-Optimized** - DOCX output designed for applicant tracking systems
-  **Type Safety** - Full type hints with Python 3.12+ syntax

### Project Structure

```
src/job_mcp/
├── server.py                          # MCP server entry point
├── config.py                          # Configuration (model, limits, paths)
├── exceptions.py                      # Custom exception hierarchy
├── tools/                             # MCP tool wrappers
│   ├── extract_job_requirements_tool.py
│   ├── match_resume_to_job_tool.py
│   ├── rewrite_resume_for_job_tool.py
│   └── export_resume_docx_tool.py
├── services/                          # Business logic layer
│   ├── extract_job_requirements_service.py
│   ├── match_resume_to_job_service.py
│   ├── rewrite_resume_for_job_service.py
│   └── export_resume_docx_service.py
├── adapters/                          # External integrations
│   ├── gemini_client.py              # Gemini AI client
│   └── job_page_fetcher.py           # Job scraping (httpx + BeautifulSoup)
├── utils/                             # Shared utilities
│   ├── gemini_helpers.py             # JSON parsing, fence stripping
│   ├── read_resume.py                # Resume file readers (.txt, .md, .docx)
│   ├── export_resume_docx.py         # DOCX generation
│   ├── validation.py                 # Input validation
│   └── logger.py                     # Logging configuration
└── prompts/                           # AI prompt templates
    └── system_prompt.txt
```

### Tool Details

####  Extract Job Requirements

**Purpose**: Parse job postings into structured data

**Input**:
- `job_url` (optional): URL to job posting
- `job_text` (optional): Raw job description text

**Output**:
```json
{
  "tech_stack": ["Python", "React", "PostgreSQL"],
  "experience_level": "3-5 years",
  "soft_skills": ["Communication", "Team leadership"],
  "responsibilities": ["..."],
  "requirements": ["..."]
}
```

####  Match Resume to Job

**Purpose**: Score resume fit and identify gaps

**Input**:
- Job requirements (from tool 1)
- Resume text or file path

**Output**:
```json
{
  "match_score": 78,
  "strengths": ["Strong Python experience", "..."],
  "gaps": ["Limited React experience", "..."],
  "missing_keywords": ["PostgreSQL", "..."],
  "recommendations": ["Highlight database work", "..."]
}
```

####  Rewrite Resume for Job

**Purpose**: Generate tailored, truthful resume

**Input**:
- Job requirements
- Match analysis
- Original resume

**Output**:
```json
{
  "rewritten_resume": "...",
  "change_log": [
    "Emphasized Python projects in Experience section",
    "Added PostgreSQL keyword to Skills",
    "..."
  ]
}
```

####  Export Resume to DOCX

**Purpose**: Create ATS-friendly Word document

**Input**:
- Rewritten resume text

**Output**:
```json
{
  "file_path": "/path/to/output_resumes/resume_20260108_143022.docx",
  "message": "Resume exported successfully"
}
```

---

## ⚙️ Configuration

Customize settings in `src/job_mcp/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini AI model to use |
| `MAX_JOB_TEXT_LENGTH` | `18000` | Max job text characters processed |
| `MAX_RESUME_LENGTH` | `16000` | Max resume characters processed |
| `DEFAULT_OUTPUT_DIR` | `output_resumes` | Default DOCX save location |
| `SUPPORTED_RESUME_FORMATS` | `[.txt, .md, .docx]` | Accepted resume file types |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` |  Yes | Google Gemini API key |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

---

##  Development

### Running Tests

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# With coverage
pytest --cov=src/job_mcp --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Lint and auto-fix
ruff check src/ --fix

# Type checking
pyright src/

# Run all checks
black src/ && ruff check src/ --fix && pyright src/ && pytest
```

### Pre-commit Hooks (Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Now hooks run automatically on commit
```

---

##  Cost Estimation

Using **Gemini 2.5 Flash** (as of January 2026):

| Operation | Tokens (approx) | Cost |
|-----------|----------------|------|
| Extract job requirements | ~2,000 | ~$0.01 |
| Match resume | ~3,000 | ~$0.02 |
| Rewrite resume | ~5,000 | ~$0.04 |
| **Total per application** | **~10,000** | **~$0.07** |

> **Note**: Prices vary by region. Monitor usage in [Google AI Studio](https://ai.google.dev/).

---

##  Dependencies

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `beautifulsoup4` | HTML parsing for job pages |
| `google-genai` | Google Gemini AI SDK |
| `httpx` | Async HTTP client with SSL support |
| `mcp[cli]` | Model Context Protocol framework |
| `python-docx` | DOCX file generation |
| `python-dotenv` | Environment variable management |
| `truststore` | System SSL certificate integration |

### Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `black` | Code formatting |
| `ruff` | Fast Python linter |
| `pyright` | Type checking |


##  Troubleshooting

### Common Issues

#### "Missing GEMINI_API_KEY" Error

**Cause**: API key not found in environment

**Solutions**:
1. Ensure `.env` file exists in project root
2. For Claude Desktop, add API key to `env` section in config JSON
3. Check for typos in variable name

```bash
# Verify .env file
cat .env

# Should show:
GEMINI_API_KEY=your_key_here
```

---

#### Server Not Appearing in Claude Desktop

**Cause**: Configuration issues or incorrect paths

**Solutions**:
1. Verify paths use forward slashes (`/`) even on Windows
2.  Check paths are absolute, not relative
3.  Restart Claude Desktop after config changes
4. Check Claude Desktop logs for error messages

```bash
# Test server manually
python src/job_mcp/server.py

# Should show:
MCP Server starting...
```
---
<div align="center">
**Made with ❤️ for job seekers everywhere**

</div>
