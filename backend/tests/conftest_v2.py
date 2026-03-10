"""
Shared fixtures for v2 tests.

Provides sample document bytes, mock ParseResult, and sample schema instances
for use across all v2 test modules.
"""

import io

import pytest

from v2.parsers.base import ParseResult
from v2.schemas.common import (
    BrandschutzKlasse,
    FieldSource,
    MaterialTyp,
    OeffnungsArt,
    SchallschutzKlasse,
    ZargenTyp,
)
from v2.schemas.extraction import ExtractedDoorPosition


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes for testing.

    Creates a tiny 1-page PDF with a simple text content.
    This is a hardcoded minimal valid PDF structure.
    """
    # Minimal valid PDF 1.0 structure
    pdf_content = (
        b"%PDF-1.0\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 44 >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (Tuer Nr. 1.01) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000360 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n434\n%%EOF"
    )
    return pdf_content


@pytest.fixture
def sample_docx_bytes() -> bytes:
    """Minimal valid DOCX bytes for testing.

    Uses python-docx to create in-memory DOCX with a paragraph and table.
    """
    from docx import Document

    doc = Document()
    doc.add_paragraph("Tuerliste Projekt Test")

    table = doc.add_table(rows=3, cols=4)
    headers = ["Tuer Nr.", "Breite", "Hoehe", "Brandschutz"]
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    # Row 1
    for i, val in enumerate(["1.01", "1000", "2100", "EI30"]):
        table.rows[1].cells[i].text = val
    # Row 2
    for i, val in enumerate(["1.02", "900", "2050", "EI60"]):
        table.rows[2].cells[i].text = val

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def sample_xlsx_bytes() -> bytes:
    """Minimal valid XLSX bytes for testing.

    Creates an in-memory workbook simulating a Tuerliste
    with columns like Tuer Nr., Breite, Hoehe, Brandschutz.
    """
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Tuerliste"

    # Header row
    headers = [
        "Tuer Nr.", "Bezeichnung", "Raum", "Breite (mm)",
        "Hoehe (mm)", "Brandschutz", "Schallschutz (dB)",
        "Material", "Anzahl"
    ]
    ws.append(headers)

    # Data rows
    ws.append(["1.01", "Buerotuere", "B101", 1000, 2100, "EI30", 32, "Holz", 1])
    ws.append(["1.02", "Flurtuere", "F201", 900, 2050, "EI60", 37, "Stahl", 2])
    ws.append(["1.03", "WC-Tuere", "WC01", 800, 2000, "", 27, "Holz", 1])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def mock_parse_result() -> ParseResult:
    """Returns a ParseResult with sample data."""
    return ParseResult(
        text="| Tuer Nr. | Breite | Hoehe | Brandschutz |\n|---|---|---|---|\n| 1.01 | 1000 | 2100 | EI30 |",
        format="xlsx",
        page_count=1,
        warnings=[],
        metadata={"sheet_names": ["Tuerliste"], "method": "openpyxl"},
        source_file="test_tuerliste.xlsx",
        tables=["| Tuer Nr. | Breite | Hoehe | Brandschutz |\n|---|---|---|---|\n| 1.01 | 1000 | 2100 | EI30 |"],
    )


@pytest.fixture
def sample_door_position() -> ExtractedDoorPosition:
    """Returns an ExtractedDoorPosition with realistic test data."""
    return ExtractedDoorPosition(
        positions_nr="1.01",
        positions_bezeichnung="Buerotuere Typ A",
        raum_nr="B101",
        raum_bezeichnung="Buero Geschaeftsleitung",
        geschoss="EG",
        breite_mm=1000,
        hoehe_mm=2100,
        wandstaerke_mm=150,
        brandschutz_klasse=BrandschutzKlasse.EI30,
        rauchschutz=True,
        schallschutz_klasse=SchallschutzKlasse.RW_32,
        schallschutz_db=32,
        material_blatt=MaterialTyp.HOLZ,
        material_zarge=ZargenTyp.UMFASSUNGSZARGE,
        oeffnungsart=OeffnungsArt.DREHFLUEGEL,
        anschlag_richtung="DIN links",
        oberflaeche="CPL Weiss",
        drueckergarnitur="Edelstahl gebuerstet",
        schlossart="Einsteckschloss BB",
        anzahl=1,
        quellen={
            "breite_mm": FieldSource(
                dokument="tuerliste.xlsx",
                zeile=5,
                zelle="D5",
                sheet="Tuerliste",
                konfidenz=0.95,
            ),
            "brandschutz_klasse": FieldSource(
                dokument="tuerliste.xlsx",
                zeile=5,
                zelle="F5",
                sheet="Tuerliste",
                konfidenz=0.99,
            ),
        },
    )
