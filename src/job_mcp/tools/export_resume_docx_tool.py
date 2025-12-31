from __future__ import annotations

import logging
from typing import Any

from job_mcp.utils.export_resume_docx import export_resume_to_docx

logger = logging.getLogger(__name__)


async def export_resume_docx_tool(
    rewritten_resume: str,
    output_dir: str = "output_resumes",
    file_name: str | None = None,
    add_timestamp: bool = True,
) -> dict[str, Any]:
    """
    Tool 4:
    Save rewritten resume as DOCX in a local folder.

    Inputs:
      - rewritten_resume: string (the final resume text)
      - output_dir: folder name/path
      - file_name: base file name (no extension needed)
      - add_timestamp: add timestamp suffix to avoid overwriting

    Output:
      - { "saved_path": "...", "file_name": "...", "output_dir": "..." }
    """
    logger.info(f"Exporting resume to DOCX: {output_dir}")

    saved_path = export_resume_to_docx(
        resume_text=rewritten_resume,
        output_dir=output_dir,
        file_name=file_name,
        add_timestamp=add_timestamp,
    )

    logger.info(f"Resume successfully saved to: {saved_path}")

    return {
        "saved_path": saved_path,
        "file_name": file_name,
        "output_dir": output_dir,
        "add_timestamp": add_timestamp,
    }
