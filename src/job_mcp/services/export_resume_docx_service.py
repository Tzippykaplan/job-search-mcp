
from __future__ import annotations

import logging
from typing import Any

from job_mcp.utils.export_resume_docx import export_resume_to_docx

logger = logging.getLogger(__name__)


class ExportResumeDocxService:
    """Service for exporting resumes to DOCX format."""

    async def export(
        self,
        resume_text: str,
        output_dir: str = "output_resumes",
        file_name: str | None = None,
        add_timestamp: bool = True,
    ) -> dict[str, Any]:
        """
        Export resume text as a DOCX file.
        
        Args:
            resume_text: The resume content as plain text.
            output_dir: Directory to save the file (default: "output_resumes").
            file_name: Base filename without extension (default: "rewritten_resume").
            add_timestamp: Whether to append timestamp to filename (default: True).
        
        Returns:
            Dictionary containing:
                - saved_path: Absolute path to the saved DOCX file
                - output_dir: Directory where file was saved
                - add_timestamp: Whether timestamp was added
        """
        logger.info("Exporting resume to DOCX: %s", output_dir)

        saved_path = export_resume_to_docx(
            resume_text=resume_text,
            output_dir=output_dir,
            file_name=file_name,
            add_timestamp=add_timestamp,
        )

        logger.info("Resume successfully saved to: %s", saved_path)

        return {
            "saved_path": saved_path,
            "output_dir": output_dir,
            "add_timestamp": add_timestamp,
        }
