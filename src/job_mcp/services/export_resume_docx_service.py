from __future__ import annotations

import logging
from typing import Any

from job_mcp.utils.export_resume_docx import export_resume_to_docx

logger = logging.getLogger(__name__)


class ExportResumeDocxService:
    async def export(
        self,
        rewritten_resume: str,
        output_dir: str = "output_resumes",
        file_name: str | None = None,
        add_timestamp: bool = True,
    ) -> dict[str, Any]:
        logger.info("Exporting resume to DOCX: %s", output_dir)

        saved_path = export_resume_to_docx(
            resume_text=rewritten_resume,
            output_dir=output_dir,
            file_name=file_name,
            add_timestamp=add_timestamp,
        )

        logger.info("Resume successfully saved to: %s", saved_path)

        return {
            "saved_path": saved_path,
            "file_name": file_name,
            "output_dir": output_dir,
            "add_timestamp": add_timestamp,
        }
