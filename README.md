#  Job Search MCP Server

<div align="center">

**AI-Powered Resume Tailoring for the Modern Job Search**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Tests: 92 Passing](https://img.shields.io/badge/tests-92%20passing-brightgreen.svg)](#development)
[![Test Coverage: 83%](https://img.shields.io/badge/coverage-83%25-brightgreen.svg)](#development)

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Usage](#usage) • [Development](#development)

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

### Technical Highlights

- **Async Architecture** - Fast, non-blocking I/O
-  **Type-Safe** - Full Python 3.12+ type hints
-  **92 Unit Tests** - Comprehensive test coverage
- **Rate Limiting** - Smart API quota management

### Design Philosophy

- **Layered Architecture** - Tools → Services → Adapters → Utils
- **Truthful AI** - Never invents fake experience
- **ATS-Optimized** - Clean DOCX output for applicant tracking systems

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

**Output** (success):
```json
{
  "source": "job_url"|"job_text",
  "job_url": "https://..."|null,
  "extracted": {
    "title": "Senior Python Engineer"|null,
    "company": "TechCorp Inc."|null,
    "location": "Remote"|null,
    "years_experience": ["5+ years Python", "3+ years React"],
    "must_have_tech": ["Python", "React", "PostgreSQL"],
    "nice_to_have_tech": ["Docker", "Kubernetes"],
    "soft_skills": ["Communication", "Team leadership"],
    "notes": ["Remote with quarterly onsite meetings"]
  }
}
```

**Output** (scrape blocked):
```json
{
  "source": "job_url",
  "job_url": "https://...",
  "error": "blocked_by_site",
  "message": "Site blocked scraping (403) or empty page. Paste the job content into job_text instead."
}
```

####  Match Resume to Job

**Purpose**: Score resume fit and identify gaps

**Input**:
- `job_requirements`: Output of `extract_job_requirements` (or just its "extracted" dict)
- `resume_text` (optional): Resume content as plain text
- `resume_file_path` (optional): Path to resume file (.txt, .md, .docx)

**Output**:
```json
{
  "score": 78,
  "matched_keywords": ["Python", "React", "AWS"],
  "missing_keywords": ["PostgreSQL", "Kubernetes"],
  "strengths": [
    "8 years Python experience (exceeds 5yr requirement)",
    "Led team of 6 engineers"
  ],
  "gaps": [
    "No PostgreSQL experience mentioned",
    "Limited Kubernetes background"
  ]
}
```

####  Rewrite Resume for Job

**Purpose**: Generate tailored, truthful resume

**Input**:
- `job_requirements`: Output of `extract_job_requirements` (or just its "extracted" dict)
- `match_result`: Output of `match_resume_to_job`
- `resume_text` (optional): Resume content as plain text
- `resume_file_path` (optional): Path to resume file (.txt, .md, .docx)

**Output**:
```json
{
  "sections": {
    "Summary": "Senior Full Stack Engineer with 8+ years...",
    "Skills": "Languages: Python, JavaScript, TypeScript\nFrameworks: React, Django...",
    "Experience": "Senior Software Engineer | TechCorp\n2020-Present\n• Developed...",
    "Projects": "E-commerce Platform\nPython, React, PostgreSQL\n• Built...",
    "Education": "B.S. Computer Science | MIT | 2015"
  },
  "rewritten_resume": "Summary\n\nSenior Full Stack Engineer with 8+ years...\n\nSkills\n...",
  "changes": [
    "Moved React and TypeScript to top of Skills section",
    "Emphasized Python projects in Experience section",
    "Rephrased team collaboration points to highlight leadership"
  ],
  "warnings": [
    "No Kubernetes experience - this is a must-have requirement",
    "Limited PostgreSQL background - consider adding database coursework"
  ]
}
```

####  Export Resume to DOCX

**Purpose**: Create ATS-friendly Word document

**Input**:
- `rewritten_resume`: Final resume text (typically from `rewrite_resume_for_job_tool()["rewritten_resume"]`)
- `output_dir` (optional): Directory to save file (default: `"output_resumes"`)
- `file_name` (optional): Base file name without extension
- `add_timestamp` (optional): Append timestamp to avoid overwriting (default: `true`)

**Output**:
```json
{
  "saved_path": "output_resumes/resume_2026-01-09_143052.docx",
  "output_dir": "output_resumes",
  "add_timestamp": true
}
```

**Features**:
- Clean, ATS-friendly formatting
- Automatic timestamp in filename (optional)
- Saved to configurable directory

---

## Configuration

Key settings in `src/job_mcp/config.py`:
- `GEMINI_MODEL` - AI model (default: `gemini-2.5-flash`)
- `GEMINI_MAX_REQUESTS_PER_MINUTE` - Rate limit (default: `60`)
- `MAX_RESUME_LENGTH` - Max resume size (default: `16000` chars)
- `DEFAULT_OUTPUT_DIR` - DOCX save location (default: `output_resumes`)

**Rate Limiting**: Automatic API quota management prevents throttling. Configurable limit, shared across instances.

---

##  Development

### Running Tests

```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest tests/unit/        # Specific suite
pytest --cov=src/job_mcp  # With coverage report
```

**Test Statistics:**
- 92 unit tests
- 83% code coverage
- All tests passing

### Code Quality Tools

The project uses the following tools (install with `pip install -e ".[dev]"`):

```bash
pytest                    # Test runner
pytest-cov                # Coverage reporting
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

---

##  Troubleshooting

### Missing GEMINI_API_KEY

**Cause**: API key not configured

**Solutions**:
- Add to `.env` file in project root
- Or add to Claude Desktop config `env` section

### Server Not Appearing in Claude Desktop

**Cause**: Configuration issues or incorrect paths

**Solutions**:
1. Verify paths use forward slashes (`/`) even on Windows
2. Check paths are absolute, not relative
3. Restart Claude Desktop after config changes
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
