"""
═══════════════════════════════════════════════════════════════════════════════
Document Parser Service – Production-Grade
Konvertiert Dateien (PDF, Excel, Word, TXT) zu Text mit Error-Handling
═══════════════════════════════════════════════════════════════════════════════
"""

import io
import logging
from pathlib import Path
from typing import Optional, Tuple

from services.error_handler import FileError, ProcessingError, ErrorCode

logger = logging.getLogger(__name__)


class DocumentParser:
    """Hauptklasse für Dokumentenanalyse"""
    
    SUPPORTED_FORMATS = {
        ".pdf": "PDF",
        ".xlsx": "Excel",
        ".xls": "Excel",
        ".xlsm": "Excel",
        ".docx": "Word",
        ".doc": "Word",
        ".txt": "Text"
    }
    
    MAX_TEXT_LENGTH = 100000  # 100k Zeichen max
    
    @staticmethod
    def get_format(filename: str) -> Optional[str]:
        """Gibt Format zurück oder None"""
        ext = Path(filename).suffix.lower()
        return DocumentParser.SUPPORTED_FORMATS.get(ext)
    
    @staticmethod
    def is_supported(filename: str) -> bool:
        """Prüft ob Datei unterstützt wird"""
        return DocumentParser.get_format(filename) is not None


def parse_document_bytes(content: bytes, ext: str) -> str:
    """
    Parst Dokument aus Bytes und gibt Text zurück.
    
    Args:
        content: Datei-Bytes
        ext: Dateiendung (z.B. ".pdf")
        
    Returns:
        Extrahierter Text
        
    Raises:
        FileError: Wenn Format nicht unterstützt oder Parsing fehlschlägt
    """
    if not content:
        raise FileError(
            ErrorCode.FILE_PARSE_ERROR,
            "Datei ist leer",
            filename=ext
        )
    
    ext = ext.lower()
    
    try:
        if ext == ".pdf":
            return _parse_pdf_bytes(content)
        elif ext in (".xlsx", ".xls", ".xlsm"):
            return _parse_excel_bytes(content)
        elif ext in (".docx", ".doc"):
            return _parse_word_bytes(content)
        elif ext == ".txt":
            text = content.decode("utf-8", errors="replace").strip()
            if not text:
                raise FileError(
                    ErrorCode.FILE_PARSE_ERROR,
                    "Textdatei ist leer",
                    filename=ext
                )
            return text
        else:
            raise FileError(
                ErrorCode.INVALID_FILE,
                f"Format '{ext}' wird nicht unterstützt",
                filename=ext
            )
    except FileError:
        raise
    except Exception as e:
        logger.exception(f"Parsing fehlgeschlagen für {ext}")
        raise FileError(
            ErrorCode.FILE_PARSE_ERROR,
            f"Konnte {ext} nicht parsen: {str(e)}",
            filename=ext
        )


def parse_document(file_path: str) -> str:
    """
    Parst Dokumentdatei und gibt Text zurück.
    Wrapper für Rückwärtskompatibilität.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileError(
            ErrorCode.FILE_NOT_FOUND,
            f"Datei nicht gefunden: {file_path}",
            filename=str(path)
        )
    
    try:
        with open(path, "rb") as f:
            content = f.read()
        return parse_document_bytes(content, path.suffix)
    except FileError:
        raise
    except Exception as e:
        logger.exception(f"Datei-Read fehlgeschlagen: {file_path}")
        raise FileError(
            ErrorCode.FILE_PARSE_ERROR,
            f"Konnte Datei nicht lesen: {str(e)}",
            filename=str(path)
        )


def parse_pdf_specs_bytes(content: bytes, max_chars: int = 8000) -> str:
    """
    Parst Spezifikations-PDF mit limitierter Länge.
    
    Args:
        content: PDF-Bytes
        max_chars: Max Zeichen zum Extrahieren
        
    Returns:
        Extrahierter Text (limitiert)
    """
    if not content:
        return ""
    
    try:
        import pdfplumber
        
        text_parts = []
        total_chars = 0
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages[:30], 1):  # Max 30 Seiten
                if total_chars >= max_chars:
                    break
                
                # Text extrahieren
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(f"--- Seite {page_num} ---\n{page_text}")
                        total_chars += len(page_text)
                except Exception as e:
                    logger.warning(f"Text-Extraktion Seite {page_num} fehlgeschlagen: {e}")
                
                # Tabellen extrahieren
                try:
                    tables = page.extract_tables()
                    for table in tables or []:
                        if table and total_chars < max_chars:
                            table_text = _table_to_text(table)
                            if table_text:
                                text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")
                                total_chars += len(table_text)
                except Exception as e:
                    logger.debug(f"Tabellen-Extraktion Seite {page_num} fehlgeschlagen: {e}")
        
        text = "\n\n".join(text_parts)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[... Text gekürzt]"
        
        return text if text.strip() else "[PDF konnte nicht vollständig gelesen werden]"
    
    except Exception as e:
        logger.exception(f"PDF-Specs Parsing fehlgeschlagen")
        return f"[PDF konnte nicht gelesen werden: {str(e)}]"


def parse_pdf_specs(file_path: str, max_chars: int = 8000) -> str:
    """Wrapper für Rückwärtskompatibilität"""
    path = Path(file_path)
    if not path.exists():
        return f"[Datei nicht gefunden: {file_path}]"
    
    try:
        with open(path, "rb") as f:
            content = f.read()
        return parse_pdf_specs_bytes(content, max_chars)
    except Exception as e:
        logger.exception(f"PDF-Specs Read fehlgeschlagen: {file_path}")
        return f"[Datei konnte nicht gelesen werden: {str(e)}]"


# ─────────────────────────────────────────────────────────────────────────────
# INTERNE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _parse_pdf_bytes(content: bytes) -> str:
    """Extrahiert Text aus PDF mit pdfplumber"""
    import pdfplumber
    
    text_parts = []
    
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if not pdf.pages:
                raise FileError(
                    ErrorCode.FILE_PARSE_ERROR,
                    "PDF hat keine Seiten",
                    filename=".pdf"
                )
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Text
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(f"--- Seite {page_num} ---\n{page_text}")
                    
                    # Tabellen
                    tables = page.extract_tables()
                    for table in tables or []:
                        if table:
                            table_text = _table_to_text(table)
                            if table_text:
                                text_parts.append(f"[Tabelle Seite {page_num}]\n{table_text}")
                
                except Exception as e:
                    logger.warning(f"Seite {page_num} Extraktion fehlgeschlagen: {e}")
                    continue
        
        result = "\n\n".join(text_parts)
        if not result.strip():
            raise FileError(
                ErrorCode.FILE_PARSE_ERROR,
                "PDF ist leer oder konnte nicht gelesen werden",
                filename=".pdf"
            )
        
        return result[:DocumentParser.MAX_TEXT_LENGTH]
    
    except FileError:
        raise
    except Exception as e:
        raise FileError(
            ErrorCode.FILE_PARSE_ERROR,
            f"PDF-Parsing fehlgeschlagen: {str(e)}",
            filename=".pdf"
        )


def _parse_excel_bytes(content: bytes) -> str:
    """Extrahiert Text aus Excel mit pandas"""
    import pandas as pd
    
    text_parts = []
    
    try:
        buf = io.BytesIO(content)
        xl = pd.ExcelFile(buf)
        
        if not xl.sheet_names:
            raise FileError(
                ErrorCode.FILE_PARSE_ERROR,
                "Excel hat keine Tabellenblätter",
                filename=".xlsx"
            )
        
        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)
                df = df.fillna("")
                
                if df.empty:
                    continue
                
                text_parts.append(f"=== {sheet_name} ===")
                text_parts.append(df.to_string(index=False))
            
            except Exception as e:
                logger.warning(f"Sheet '{sheet_name}' Parsing fehlgeschlagen: {e}")
                continue
        
        result = "\n\n".join(text_parts)
        if not result.strip():
            raise FileError(
                ErrorCode.FILE_PARSE_ERROR,
                "Excel ist leer",
                filename=".xlsx"
            )
        
        return result[:DocumentParser.MAX_TEXT_LENGTH]
    
    except FileError:
        raise
    except Exception as e:
        raise FileError(
            ErrorCode.FILE_PARSE_ERROR,
            f"Excel-Parsing fehlgeschlagen: {str(e)}",
            filename=".xlsx"
        )


def _parse_word_bytes(content: bytes) -> str:
    """Extrahiert Text aus Word mit python-docx"""
    from docx import Document
    
    text_parts = []
    
    try:
        doc = Document(io.BytesIO(content))
        
        # Paragraphen
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        # Tabellen
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    text_parts.append(" | ".join(cells))
        
        result = "\n".join(text_parts)
        if not result.strip():
            raise FileError(
                ErrorCode.FILE_PARSE_ERROR,
                "Word-Dokument ist leer",
                filename=".docx"
            )
        
        return result[:DocumentParser.MAX_TEXT_LENGTH]
    
    except FileError:
        raise
    except Exception as e:
        raise FileError(
            ErrorCode.FILE_PARSE_ERROR,
            f"Word-Parsing fehlgeschlagen: {str(e)}",
            filename=".docx"
        )


def _table_to_text(table: list) -> str:
    """Konvertiert Tabelle (Liste von Listen) zu Text"""
    if not table:
        return ""
    
    rows = []
    for row in table:
        if row:
            cells = [str(cell).strip() if cell else "" for cell in row]
            rows.append(" | ".join(cells))
    
    return "\n".join(rows)


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        text = parse_document(sys.argv[1])
        print(f"Extrahiert: {len(text)} Zeichen")
        print(text[:500])
