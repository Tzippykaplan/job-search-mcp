from __future__ import annotations
from typing import Protocol


class ResumeExporter(Protocol):
    def export(self, resume_text: str, output_dir: str, file_name: str | None, add_timestamp: bool) -> str:
        """Export resume and return output file path."""
