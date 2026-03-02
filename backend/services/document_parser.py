"""
Document Parser – Converts uploaded files (PDF, Excel, Word, TXT) to plain text.
"""

import os
import io
from pathlib import Path


def parse_document(file_path: str) -> str:
    """
    Parse a document file and return its text content.
    Supports: .pdf, .xlsx, .xls, .docx, .doc, .txt
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext in (".xlsx", ".xls"):
        return _parse_excel(file_path)
    elif ext in (".docx", ".doc"):
        return _parse_word(file_path)
    elif ext == ".txt":
        return _parse_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _parse_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Seite {page_num} ---\n{page_text}")

                # Also extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        table_text = _table_to_text(table)
                        if table_text:
                            text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")

        return "\n\n".join(text_parts) if text_parts else ""
    except Exception as e:
        raise RuntimeError(f"PDF parsing failed: {e}")


def _parse_excel(file_path: str) -> str:
    """Extract text from Excel using pandas."""
    try:
        import pandas as pd

        text_parts = []
        xl = pd.ExcelFile(file_path)

        for sheet_name in xl.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
            df = df.fillna("")

            # Skip empty sheets
            if df.empty:
                continue

            text_parts.append(f"=== Tabellenblatt: {sheet_name} ===")
            # Convert to readable text
            text_parts.append(df.to_string(index=False))

        return "\n\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(f"Excel parsing failed: {e}")


def _parse_word(file_path: str) -> str:
    """Extract text from Word documents using python-docx."""
    try:
        from docx import Document

        doc = Document(file_path)
        text_parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Also extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                )
                if row_text:
                    text_parts.append(row_text)

        return "\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(f"Word parsing failed: {e}")


def _parse_text(file_path: str) -> str:
    """Read plain text file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Text file reading failed: {e}")


def parse_pdf_specs(file_path: str, max_chars: int = 8000) -> str:
    """
    Parse a specification PDF for supplementary context.
    Focuses on text-based specs (LV, Türtypicals, Türbuch).
    Truncates at max_chars to stay within token budget.
    """
    try:
        text = _parse_pdf(file_path)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [gekürzt]"
        return text
    except Exception as e:
        return f"[PDF konnte nicht gelesen werden: {e}]"


def _table_to_text(table: list) -> str:
    """Convert a table (list of lists) to formatted text."""
    if not table:
        return ""
    rows = []
    for row in table:
        if row:
            cells = [str(cell).strip() if cell else "" for cell in row]
            rows.append(" | ".join(cells))
    return "\n".join(rows)
