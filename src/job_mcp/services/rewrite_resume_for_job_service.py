from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from job_mcp.config import MAX_RESUME_LENGTH
from job_mcp.adapters.gemini_client import GeminiLLMClient
from job_mcp.utils.gemini_helpers import as_list, parse_llm_json_response
from job_mcp.utils.read_resume import read_resume_any
from job_mcp.exceptions import ValidationError, LLMResponseError, FileReadError

logger = logging.getLogger(__name__)


class RewriteResumeService:    
    def __init__(
        self,
        llm: GeminiLLMClient | None = None,
        resume_reader: Callable[[str], str] = read_resume_any,
    ) -> None:
        self._llm = llm or GeminiLLMClient()
        self._resume_reader = resume_reader

    async def rewrite_resume_for_job(
        self,
        job_requirements: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str | None = None,
        resume_file_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info("Starting resume rewrite", extra={
            "source": "file" if resume_file_path else "text"
        })
        
        if resume_file_path:
            logger.info("Reading resume from file", extra={"path": resume_file_path})
            resume_text = self._resume_reader(resume_file_path)
            logger.debug("Resume loaded from file", extra={"length": len(resume_text)})

        resume_text = (resume_text or "").strip()
        if not resume_text:
            logger.error("Validation failed: no resume text provided")
            raise ValidationError("Provide either resume_text or resume_file_path")

        extracted = (job_requirements or {}).get("extracted", job_requirements)
        return await self._rewrite_resume_with_llm(extracted, match_result, resume_text)

    async def _rewrite_resume_with_llm(
        self,
        job_requirements: dict[str, Any],
        match_result: dict[str, Any],
        resume_text: str,
    ) -> dict[str, Any]:
        resume_text = self._compact_text(resume_text)
        if not resume_text:
            logger.error("Resume text is empty after compacting")
            raise ValidationError("resume_text is required and cannot be empty")

        logger.debug("Resume text compacted", extra={"final_length": len(resume_text)})

        job_requirements = (job_requirements or {}).get("extracted", job_requirements)

        filtered_job_requirements = {
            "title": job_requirements.get("title") or job_requirements.get("role_title"),
            "must_have_tech": job_requirements.get("must_have_tech", []),
            "nice_to_have_tech": job_requirements.get("nice_to_have_tech", []),
            "years_experience": job_requirements.get("years_experience"),
            "responsibilities": job_requirements.get("responsibilities", []),
            "notes": job_requirements.get("notes", []),
        }

        filtered_match_result = {
            "score": match_result.get("score") if isinstance(match_result, dict) else None,
            "matched_keywords": match_result.get("matched_keywords", []) if isinstance(match_result, dict) else [],
            "missing_keywords": match_result.get("missing_keywords", []) if isinstance(match_result, dict) else [],
            "strengths": match_result.get("strengths", []) if isinstance(match_result, dict) else [],
            "gaps": match_result.get("gaps", []) if isinstance(match_result, dict) else [],
        }

        truncated_resume_text = resume_text[:MAX_RESUME_LENGTH]
        prompt = self._build_rewrite_prompt(filtered_job_requirements, filtered_match_result, truncated_resume_text)
        
        logger.info("Calling Gemini API for resume rewrite", extra={"prompt_length": len(prompt)})
        llm_response = await self._llm.generate_text(prompt)
        logger.debug("Received LLM response", extra={"response_length": len(llm_response)})

        parsed_rewrite_result = parse_llm_json_response(
            llm_response, "resume rewrite", logger
        )

        # Check if result is a wrapped array (from robust_json_loads)
        if "data" in parsed_rewrite_result and len(parsed_rewrite_result) == 1:
            logger.error("LLM returned array instead of object")
            raise LLMResponseError("Gemini returned JSON but not an object for rewrite_resume")

        if not isinstance(parsed_rewrite_result, dict):
            logger.error("LLM returned non-dict JSON", extra={"type": type(parsed_rewrite_result).__name__})
            raise LLMResponseError("Gemini returned JSON but not an object for rewrite_resume")

        return self._normalize_rewrite_result(parsed_rewrite_result)

    @staticmethod
    def _compact_text(s: str) -> str:
        s = (s or "").replace("\r\n", "\n")
        s = "\n".join(line.rstrip() for line in s.splitlines())
        s = re.sub(r"\n{3,}", "\n\n", s).strip()
        return s

    @staticmethod
    def _build_rewrite_prompt(
        filtered_job_requirements: dict[str, Any],
        filtered_match_result: dict[str, Any],
        truncated_resume_text: str,
    ) -> str:
        return f"""You are an expert ATS (Applicant Tracking System) resume optimizer. Your task is to rewrite a resume to better align with specific job requirements while maintaining complete truthfulness.

OUTPUT FORMAT:
- Return ONLY valid JSON
- No markdown, no code fences (no ```), no explanatory text
- Raw JSON object only

CORE OBJECTIVE:
Optimize the resume to maximize ATS score and recruiter appeal for the target role while staying 100% truthful to the candidate's actual experience.

STRICT TRUTHFULNESS RULES (CRITICAL):
1. NEVER add skills, technologies, or experience not explicitly present in the original resume
2. NEVER fabricate projects, roles, achievements, or certifications
3. NEVER inflate years of experience or job titles
4. NEVER claim expertise in technologies only briefly mentioned
5. DO NOT remove any truthful information - if less relevant, keep but deprioritize or condense

ALLOWED OPTIMIZATIONS:
1. Reorder sections and bullet points to emphasize relevant experience first
2. Rephrase descriptions to highlight relevant skills and use job-specific keywords
3. Quantify achievements where specific numbers exist (e.g., "increased performance by 40%")
4. Expand on relevant projects/roles and condense less relevant ones
5. Align terminology with job posting (e.g., "frontend" → "front-end" if job uses that)
6. Strengthen weak phrasing (e.g., "helped with" → "contributed to", "worked on" → "developed")

FORMATTING GUIDELINES:
- Target length: ~1 page equivalent (~500-700 words)
- Use bullet points for readability
- Keep sections clearly separated with headers
- Use action verbs (developed, led, implemented, designed, optimized)
- Be concise but specific

JOB REQUIREMENTS (FILTERED):
{json.dumps(filtered_job_requirements, ensure_ascii=False)}

MATCH ANALYSIS (FILTERED):
{json.dumps(filtered_match_result, ensure_ascii=False)}

ORIGINAL RESUME:
\"\"\"{truncated_resume_text}\"\"\"

OUTPUT JSON SCHEMA (ALL fields required):
{{
  "sections": {{
    "Summary": string,
    "Skills": string,
    "Experience": string,
    "Projects": string,
    "Education": string
  }},
  "rewritten_resume": string,
  "changes": string[],
  "warnings": string[]
}}

FIELD DEFINITIONS:

1. sections (object): Individual resume sections as strings
   - Summary: 2-3 sentence professional summary highlighting relevant experience and strengths
   - Skills: Organized technical skills (languages, frameworks, tools, etc.) - prioritize matched keywords
   - Experience: Work history with bullet points emphasizing relevant achievements
   - Projects: Notable projects showcasing relevant skills (if applicable)
   - Education: Degrees, certifications, relevant coursework
   - Use "" (empty string) for sections where no relevant information exists

2. rewritten_resume: Complete final resume text assembled in this exact order:
   Summary → Skills → Experience → Projects → Education
   Must be properly formatted with section headers and spacing

3. changes (array): Short bullet points explaining key improvements made
   Examples:
   - "Moved React and TypeScript to top of Skills section to match must-have requirements"
   - "Expanded description of microservices project to highlight Kubernetes experience"
   - "Rephrased team collaboration points to emphasize leadership experience"
   - "Reordered work experience to prioritize relevant backend development role"

4. warnings (array): Critical gaps that cannot be ethically addressed
   Examples:
   - "No Kubernetes experience - this is a must-have requirement"
   - "Limited leadership experience - job requires managing teams"
   - "Missing cloud certifications preferred by employer"

SECTION-SPECIFIC GUIDANCE:

Summary:
- Lead with job title match (e.g., "Senior Full Stack Engineer with 8+ years experience")
- Mention 2-3 most relevant strengths from matched_keywords
- Keep to 2-3 sentences maximum

Skills:
- Prioritize matched_keywords at the top
- Group logically (e.g., "Languages: Python, JavaScript" / "Frameworks: React, Django")
- Only list skills present in original resume

Experience:
- Lead each role with: Job Title | Company | Dates
- For relevant roles: expand bullet points, emphasize matched skills
- For less relevant roles: condense but don't remove
- Use metrics where available (e.g., "Reduced load time by 40%")
- Start bullets with strong action verbs

Projects:
- Highlight projects that demonstrate missing or weak skills
- Include: project name, technologies used, your role, impact
- Only if meaningful projects exist in original resume

Education:
- Standard format: Degree | Institution | Year
- Include relevant coursework if it matches job requirements
- List certifications if present

Remember: Optimize for ATS and recruiter appeal, but NEVER compromise truthfulness. Return ONLY the JSON object.""".strip()

    @staticmethod
    def _normalize_rewrite_result(parsed_rewrite_result: dict[str, Any]) -> dict[str, Any]:
        """Normalize LLM response to ensure consistent structure.
        
        Handles edge cases:
        - Missing or malformed sections dict
        - Non-string section values
        - Missing rewritten_resume field (reconstructs from sections)
        
        This defensive parsing prevents downstream errors from LLM inconsistencies.
        """
        sections = parsed_rewrite_result.get("sections") if isinstance(parsed_rewrite_result, dict) else None
        if not isinstance(sections, dict):
            sections = {}

        def get_section(name: str) -> str:
            v = sections.get(name, "")
            return v if isinstance(v, str) else ""

        normalized_sections = {
            "Summary": get_section("Summary"),
            "Skills": get_section("Skills"),
            "Experience": get_section("Experience"),
            "Projects": get_section("Projects"),
            "Education": get_section("Education"),
        }

        rewritten_resume = parsed_rewrite_result.get("rewritten_resume", "")
        if not isinstance(rewritten_resume, str) or not rewritten_resume.strip():
            # If the LLM omitted the combined field, derive it deterministically from sections.
            resume_sections = []
            for key in ["Summary", "Skills", "Experience", "Projects", "Education"]:
                txt = normalized_sections[key].strip()
                if txt:
                    resume_sections.append(f"{key}\n{txt}".strip())
            rewritten_resume = "\n\n".join(resume_sections).strip()

        return {
            "sections": normalized_sections,
            "rewritten_resume": rewritten_resume,
            "changes": as_list(parsed_rewrite_result.get("changes")),
            "warnings": as_list(parsed_rewrite_result.get("warnings")),
        }
