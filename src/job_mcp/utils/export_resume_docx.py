from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re


def _safe_filename(name: str) -> str:
    """
    Make a safe filename for Windows/Linux.
    Keeps letters/numbers/space/_/- and removes the rest.
    """
    name = (name or "").strip() or "resume"
    name = re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", name)  # Windows-illegal chars
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120]  # prevent too-long filenames


def export_resume_to_docx(
    resume_text: str,
    output_dir: str = "output_resumes",
    file_name: str | None = None,
    add_timestamp: bool = True,
) -> str:
    """
    Export resume plain text to a DOCX file.

    Parameters:
      resume_text: the final resume content (string)
      output_dir: directory to save files (relative or absolute)
      file_name: optional base name (without .docx)
      add_timestamp: if True, append YYYYMMDD_HHMMSS

    Returns:
      absolute path to the generated docx file (string)
    """
    text = (resume_text or "").strip()
    if not text:
        raise ValueError("resume_text is empty")

    out_dir = Path(output_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base = _safe_filename(file_name) if file_name else "rewritten_resume"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S") if add_timestamp else ""
    final_name = f"{base}_{stamp}.docx" if stamp else f"{base}.docx"
    out_path = (out_dir / final_name).resolve()

    # python-docx
    from docx import Document

    doc = Document()

    # Convert text blocks into paragraphs (simple + ATS-friendly)
    blocks = text.split("\n")
    for line in blocks:
        line = line.rstrip()
        if line == "":
            doc.add_paragraph("")  # keep spacing
        else:
            doc.add_paragraph(line)

    doc.save(str(out_path))
    return str(out_path)
