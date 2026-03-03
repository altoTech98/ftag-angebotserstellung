"""
Document Parser – Converts uploaded files (PDF, Excel, Word, TXT) to plain text.
Supports both file-path and in-memory (bytes) parsing.
"""

import io
from pathlib import Path


def parse_document_bytes(content: bytes, ext: str) -> str:
    """
    Parse a document from raw bytes and return its text content.
    Supports: .pdf, .xlsx, .xls, .docx, .doc, .txt
    """
    ext = ext.lower()
    if ext == ".pdf":
        return _parse_pdf_bytes(content)
    elif ext in (".xlsx", ".xls"):
        return _parse_excel_bytes(content)
    elif ext in (".docx", ".doc"):
        return _parse_word_bytes(content)
    elif ext == ".txt":
        return content.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def parse_document(file_path: str) -> str:
    """
    Parse a document file and return its text content.
    Wrapper around parse_document_bytes for backward compatibility.
    """
    ext = Path(file_path).suffix.lower()
    with open(file_path, "rb") as f:
        content = f.read()
    return parse_document_bytes(content, ext)


def parse_pdf_specs_bytes(content: bytes, max_chars: int = 8000) -> str:
    """
    Parse a specification PDF from bytes for supplementary context.
    Stops early once enough text is collected.
    """
    try:
        import pdfplumber

        text_parts = []
        total_chars = 0

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                if total_chars >= max_chars:
                    break
                if page_num > 30:
                    break

                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Seite {page_num} ---\n{page_text}")
                    total_chars += len(page_text)

                tables = page.extract_tables()
                for table in tables:
                    if table:
                        table_text = _table_to_text(table)
                        if table_text:
                            text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")
                            total_chars += len(table_text)

        text = "\n\n".join(text_parts)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [gekürzt]"
        return text
    except Exception as e:
        return f"[PDF konnte nicht gelesen werden: {e}]"


def parse_pdf_specs(file_path: str, max_chars: int = 8000) -> str:
    """Wrapper for backward compatibility."""
    with open(file_path, "rb") as f:
        content = f.read()
    return parse_pdf_specs_bytes(content, max_chars)


# ---------------------------------------------------------------------------
# Internal parsers (bytes-based)
# ---------------------------------------------------------------------------

def _parse_pdf_bytes(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Seite {page_num} ---\n{page_text}")

                tables = page.extract_tables()
                for table in tables:
                    if table:
                        table_text = _table_to_text(table)
                        if table_text:
                            text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")

        return "\n\n".join(text_parts) if text_parts else ""
    except Exception as e:
        raise RuntimeError(f"PDF parsing failed: {e}")


def _parse_excel_bytes(content: bytes) -> str:
    """Extract text from Excel bytes using pandas."""
    try:
        import pandas as pd

        text_parts = []
        buf = io.BytesIO(content)
        xl = pd.ExcelFile(buf)

        for sheet_name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)
            df = df.fillna("")

            if df.empty:
                continue

            text_parts.append(f"=== Tabellenblatt: {sheet_name} ===")
            text_parts.append(df.to_string(index=False))

        return "\n\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(f"Excel parsing failed: {e}")


def _parse_word_bytes(content: bytes) -> str:
    """Extract text from Word bytes using python-docx."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(content))
        text_parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

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
