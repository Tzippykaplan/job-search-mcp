# Job Search MCP Server

An intelligent Model Context Protocol (MCP) server for job searching that helps users match their resumes to job postings and automatically optimize them using Google's Gemini AI.

## Features

 **Job Requirements Extraction** - Parse job postings from URLs or text and extract structured requirements (tech stack, years of experience, soft skills)

**Resume Matching** - Evaluate how well your resume matches a specific job with detailed feedback on strengths and gaps

 **Resume Rewriting** - Automatically rewrite your resume to better match job requirements while keeping all content truthful

**DOCX Export** - Save optimized resumes as professional Word documents ready for submission

## Installation

### Prerequisites

- Python 3.12+
- Google Gemini API key ([Get one here](https://ai.google.dev/))

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd job-search-mcp

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .

# For development (includes testing tools)
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the project root with your API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
```
## Connecting to an AI Agent (MCP)

This MCP server can be used with AI agents that support the Model Context Protocol (MCP), such as Claude Desktop and OpenAI Codex CLI.

## Option 1: Claude Desktop (Recommended)

Claude Desktop provides a graphical interface and automatically manages MCP servers on startup.

### Claude Desktop Configuration

Add the following entry to your Claude Desktop MCP configuration file:

```json
{
  "mcpServers": {
    "job-search-mcp": {
      "command": "C:\\Users\\python_projects\\job-search-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "-u",
        "C:\\Users\\python_projects\\job-search-mcp\\src\\job_mcp\\server.py"
      ],
      "cwd": "C:\\Users\\python_projects\\job-search-mcp",
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```
## Important Notes


-  **Absolute paths are recommended** for reliable execution on Windows.
-  The MCP server **starts automatically** when Claude Desktop initializes MCP tools.
-  Once connected, the agent can:
  - Analyze job posting URLs
  - Ask for your resume if it is missing
  - Match and rewrite the resume for the role
  - Export a tailored DOCX file

---

## Option 2: OpenAI Codex CLI

Codex CLI is best suited for terminal-based, agent-style workflows.

### Register the MCP Server

```bash
codex mcp add job-search-mcp -- \
  C:\Users\python_projects\job-search-mcp\.venv\Scripts\python.exe \
  -u C:\Users\python_projects\job-search-mcp\src\job_mcp\server.py
```

### Start Codex

```bash
codex
```
### Example Agent Prompt
The agent autonomously orchestrates MCP tools based on user intent, without requiring explicit step-by-step instructions.

```text
I want to apply for the following job.
Analyze this job posting end-to-end.
If my resume is missing, ask for it and tailor it to the role using the MCP tools.

URL: https://example.com/job-posting

```

## Summary

- **Claude Desktop** – best for interactive, UI-based workflows  
- **Codex CLI** – best for terminal-based, agent-style automation  

Both options expose the same MCP tools and capabilities.

## Usage

### Starting the Server

```bash
python src/job_mcp/server.py
```

Or using MCP's CLI:

```bash
mcp run src/job_mcp/server.py
```

### Tool Chain Example

The tools are designed to work together in a pipeline:

```
1. Extract Job Requirements
   Input: job_url OR job_text
   Output: {extracted: {title, company, must_have_tech, nice_to_have_tech, ...}}
   
2. Match Resume to Job
   Input: job_extracted + resume_text
   Output: {score, matched_keywords, missing_keywords, strengths, gaps}
   
3. Rewrite Resume
   Input: job_extracted + match_result + resume_text
   Output: {rewritten_resume, sections, changes, warnings}
   
4. Export to DOCX
   Input: rewritten_resume
   Output: {saved_path, file_name, output_dir}
```

### Detailed Tool Documentation

#### 1. `extract_job_requirements_tool`

Extract structured job requirements from a URL or job description.

**Inputs:**
- `job_url` (optional): URL to the job posting
- `job_text` (optional): Raw job description text (if URL doesn't work)

**Outputs:**
```json
{
  "source": "job_url|job_text",
  "job_url": "https://...",
  "extracted": {
    "title": "Software Engineer",
    "company": "TechCorp",
    "location": "San Francisco, CA",
    "years_experience": ["3+", "5+"],
    "must_have_tech": ["Python", "React", "PostgreSQL"],
    "nice_to_have_tech": ["Kubernetes", "GraphQL"],
    "soft_skills": ["Team collaboration", "Leadership"],
    "notes": ["Remote friendly", "100k-150k salary range"]
  }
}
```

#### 2. `match_resume_to_job_tool`

Evaluate how well a resume matches a job and identify gaps.

**Inputs:**
- `job_extracted`: Output from extract_job_requirements_tool
- `resume_text`: Your resume as plain text

**Outputs:**
```json
{
  "score": 75,
  "matched_keywords": ["Python", "React", "SQL"],
  "missing_keywords": ["Kubernetes", "GraphQL"],
  "strengths": [
    "5+ years of professional Python development",
    "Strong frontend experience with React",
    "Experience with PostgreSQL optimization"
  ],
  "gaps": [
    "No Kubernetes/container orchestration experience",
    "Limited GraphQL background",
    "Remote work experience not highlighted"
  ]
}
```

#### 3. `rewrite_resume_for_job`

Rewrite your resume to better match the job while keeping everything truthful.

**Inputs:**
- `job_extracted`: From tool #1
- `match_result`: From tool #2
- `resume_text` OR `resume_file_path`: Your resume (.docx, .txt, or .md)

**Outputs:**
```json
{
  "sections": {
    "Summary": "Professional summary tailored to the job...",
    "Skills": "Python, React, PostgreSQL, ...",
    "Experience": "Rewritten experience section...",
    "Projects": "Relevant projects...",
    "Education": "..."
  },
  "rewritten_resume": "Complete resume text\n\nProperly formatted...",
  "changes": [
    "Moved Python and React to top of skills",
    "Emphasized relevant database optimization experience",
    "Reordered experience by relevance to the job"
  ],
  "warnings": [
    "No Kubernetes experience in resume - consider learning it"
  ]
}
```

#### 4. `export_resume_docx`

Export your resume to a professional DOCX file.

**Inputs:**
- `rewritten_resume`: Resume text from tool #3
- `output_dir` (optional): Directory to save file (default: "output_resumes")
- `file_name` (optional): Filename without extension (default: "rewritten_resume")
- `add_timestamp` (optional): Add timestamp to filename (default: true)

**Outputs:**
```json
{
  "saved_path": "/absolute/path/to/rewritten_resume_20251230_143022.docx",
  "file_name": "rewritten_resume",
  "output_dir": "output_resumes",
  "add_timestamp": true
}
```

## Architecture

```
src/job_mcp/
├── server.py                 # MCP server entry point
├── config.py                 # Configuration constants
├── exceptions.py             # Custom exception classes
├── tools/
│   ├── extract_job_requirements_tool.py
│   ├── match_resume_to_job_tool.py
│   ├── rewrite_resume_for_job_tool.py
└── utils/
    ├── gemini_helpers.py    # Shared Gemini utilities
    ├── read_resume.py       # Resume file reading
    └── export_resume_docx.py # DOCX export logic
```

## Configuration

Edit `src/job_mcp/config.py` to adjust:

- `GEMINI_MODEL`: AI model to use (default: gemini-2.5-flash)
- `MAX_JOB_TEXT_LENGTH`: Maximum job text to process (default: 18,000 chars)
- `MAX_RESUME_LENGTH`: Maximum resume text to process (default: 16,000 chars)
- `DEFAULT_OUTPUT_DIR`: Where to save DOCX files (default: "output_resumes")

## Supported Resume Formats

The tool supports reading from:
- Plain text (.txt)
- Markdown (.md)
- Microsoft Word (.docx)

## Logging

The server logs important events at INFO level. Set environment variables to control logging:

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
```


## Development

### Code Formatting

```bash
black src/
ruff check src/ --fix
```

### Type Checking

```bash
pyright src/
```

## Cost Estimation

Using Gemini 2.5 Flash API:
- ~0.005 tokens per job (1,000 tokens ≈ $0.02)
- ~0.010 tokens per resume matching
- ~0.025 tokens per resume rewriting

**Typical workflow cost: ~$0.03-0.05 per resume optimization**

## Limitations

- Job scraping may fail if site blocks requests (use job_text workaround)
- Resume rewriting only emphasizes existing skills (cannot add new experience)
- Works best with well-formatted resumes

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request



## Support

For issues or questions:
- Check the [Troubleshooting](#error-handling) section
- Review tool descriptions in Usage section
- Check Gemini API documentation for rate limits

---

**Made with ❤️ for anyone looking for their next job.**
