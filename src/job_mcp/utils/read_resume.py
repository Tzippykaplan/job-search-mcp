from __future__ import annotations

from pathlib import Path
from job_mcp.exceptions import FileReadError


def read_text_file(path: str) -> str:
    """
    Read plain text resume file.
    """
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="ignore")


def read_docx_file(path: str) -> str:
    """
    Read DOCX resume file.
    """
    from docx import Document
    
    doc = Document(path)
    parts = []
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def read_resume_any(path: str) -> str:
    """
    Read resume from file.

    Automatically detects format (.txt, .md, .docx) and reads accordingly.

    Args:
        path: Path to resume file.

    Returns:
        Resume text content.

    Raises:
        FileReadError: If file not found or unsupported format.
    """
    p = Path(path).resolve()  # Resolve symlinks and relative paths

    if not p.exists():
        raise FileReadError(f"Resume file not found: {path}")

    ext = p.suffix.lower()
    if ext in [".txt", ".md"]:
        return read_text_file(str(p))
    if ext == ".docx":
        return read_docx_file(str(p))

    raise FileReadError(f"Unsupported resume file type: {ext}. Use .txt, .md, or .docx")

