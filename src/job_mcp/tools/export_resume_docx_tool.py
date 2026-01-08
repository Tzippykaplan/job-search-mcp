from __future__ import annotations

from typing import Any

from job_mcp.services.export_resume_docx_service import ExportResumeDocxService


async def export_resume_docx_tool(
    rewritten_resume: str,
    output_dir: str = "output_resumes",
    file_name: str | None = None,
    add_timestamp: bool = True,
) -> dict[str, Any]:
    """Export a resume text to a local DOCX file.

    Inputs:
    - rewritten_resume: final resume text (typically `rewrite_resume_for_job_tool()["rewritten_resume"]`)
    - output_dir: folder name/path
    - file_name: base file name (no extension needed)
    - add_timestamp: append timestamp to reduce overwrite risk

    Returns:
    - {"saved_path": str, "output_dir": str, "add_timestamp": bool}
    """
    export_resume_docx_service = ExportResumeDocxService()
    return await export_resume_docx_service.export(
        resume_text=rewritten_resume,
        output_dir=output_dir,
        file_name=file_name,
        add_timestamp=add_timestamp,
    )
