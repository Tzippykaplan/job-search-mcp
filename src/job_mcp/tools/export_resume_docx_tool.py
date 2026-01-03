from __future__ import annotations

from typing import Any

from job_mcp.services.export_resume_docx_service import ExportResumeDocxService


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
    service = ExportResumeDocxService()
    return await service.export(
        resume_text=rewritten_resume,
        output_dir=output_dir,
        file_name=file_name,
        add_timestamp=add_timestamp,
    )
