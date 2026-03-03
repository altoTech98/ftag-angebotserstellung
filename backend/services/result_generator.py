"""
Result Generator – Creates Machbarkeitsanalyse Excel + GAP Report in memory.

Generates a 2-sheet Excel file:
  Sheet 1: "Machbarkeitsanalyse" – matching results per door position
  Sheet 2: "GAP-Report" – items that cannot be fulfilled

All functions return bytes (no disk writes).
"""

import io
import re
from datetime import datetime


def _auto_row_height(cell_values: list[str], col_widths: list[float], base_height: float = 15.0) -> float:
    """Estimate row height based on content and column widths."""
    max_lines = 1
    for val, width in zip(cell_values, col_widths):
        if not val:
            continue
        text = str(val)
        # Count explicit newlines
        lines_in_text = text.count("\n") + 1
        # Estimate wrapped lines per text segment (approx 1.2 chars per width unit)
        chars_per_line = max(int(width * 1.2), 10)
        for segment in text.split("\n"):
            wrapped = max(1, -(-len(segment) // chars_per_line))  # ceil division
            lines_in_text += wrapped - 1
        max_lines = max(max_lines, lines_in_text)
    return max(base_height, min(max_lines * 15.0, 200.0))


def _clean_reason(entry: dict) -> str:
    """Build a human-readable reason text instead of raw compact_text."""
    status = entry.get("status", "")
    gaps = entry.get("gap_items", [])
    products = entry.get("matched_products", [])

    if status == "unmatched" and not products:
        return "Kein passendes FTAG-Produkt gefunden"

    parts = []
    if gaps:
        for g in gaps:
            # Clean up gap text
            g = re.sub(r'^\[?\d+\]\s*\|?\s*', '', str(g))
            parts.append(g)
    elif status == "matched":
        parts.append("Anforderungen erfuellt")

    return "\n".join(parts) if parts else ""


def _get_product_name(entry: dict) -> str:
    """Extract a clean product name from matched products."""
    products = entry.get("matched_products", [])
    if not products:
        return ""
    p = products[0]

    # Try known column names in order of preference
    for key in [
        "Türblatt / Verglasungsart / Rollkasten",
        "Türblattausführung",
        "_compact",
    ]:
        val = p.get(key, "")
        if val:
            # Clean up _compact format: remove "[row_idx] | Category |" prefix
            if key == "_compact":
                val = re.sub(r'^\[\d+\]\s*\|\s*\S+\s*\|\s*', '', val)
            return str(val).strip()

    # Fallback: second value in dict (first is usually category)
    keys = list(p.keys())
    for k in keys:
        if k.startswith("_"):
            continue
        val = str(p[k]).strip()
        if val and val not in ("Rahmentüre", "Zargentüre", "Futtertüre", "Schiebetüre"):
            return val
    return ""


def _get_product_variant(entry: dict) -> str:
    """Get door variant (Stumpf, Gefälzt, etc.)."""
    products = entry.get("matched_products", [])
    if not products:
        return ""
    p = products[0]
    return str(p.get("Türblattausführung", "")).strip()


def generate_result_excel(
    matching: dict,
    requirements: dict,
    result_id: str,
) -> bytes:
    """Generate the Machbarkeitsanalyse + GAP Excel. Returns raw bytes."""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    # ── Styles ──────────────────────────────────────
    header_fill = PatternFill("solid", fgColor="1F3A5F")
    green_fill = PatternFill("solid", fgColor="D4EDDA")
    yellow_fill = PatternFill("solid", fgColor="FFF3CD")
    red_fill = PatternFill("solid", fgColor="F8D7DA")
    alt_row_fill = PatternFill("solid", fgColor="F2F4F7")
    light_green = PatternFill("solid", fgColor="E8F5E9")

    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1F3A5F")
    subtitle_font = Font(name="Calibri", size=10, color="666666")
    normal_font = Font(name="Calibri", size=10)
    bold_font = Font(name="Calibri", size=10, bold=True)
    status_font_ok = Font(name="Calibri", size=10, bold=True, color="155724")
    status_font_warn = Font(name="Calibri", size=10, bold=True, color="856404")
    status_font_fail = Font(name="Calibri", size=10, bold=True, color="721C24")
    small_font = Font(name="Calibri", size=9, color="555555")

    thin_border = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )

    center_v = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_top = Alignment(horizontal="left", vertical="top", wrap_text=True)
    left_center = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # ── Sheet 1: Machbarkeitsanalyse ────────────────
    ws1 = wb.active
    ws1.title = "Machbarkeitsanalyse"
    ws1.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)

    # Column config: (header, width, alignment)
    columns = [
        ("Nr.",             5,   center_v),
        ("Tür-Nr.",        16,   left_center),
        ("Raum",           22,   left_center),
        ("Geschoss",        9,   center_v),
        ("Türtyp",         20,   left_center),
        ("FTAG Produkt",   25,   left_center),
        ("Kategorie",      15,   left_center),
        ("B x H (mm)",     14,   center_v),
        ("Brandschutz",    13,   center_v),
        ("Schallschutz",   13,   center_v),
        ("Einbruchschutz", 14,   center_v),
        ("Status",         14,   center_v),
        ("Hinweise",       45,   left_top),
    ]

    col_widths_list = [c[1] for c in columns]

    for col_idx, (header, width, _) in enumerate(columns, 1):
        col_letter = get_column_letter(col_idx)
        ws1.column_dimensions[col_letter].width = width

    # Title row
    ws1.merge_cells(f"A1:{get_column_letter(len(columns))}1")
    ws1["A1"] = "Machbarkeitsanalyse Frank Tueren AG"
    ws1["A1"].font = title_font
    ws1["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[1].height = 32

    # Subtitle row
    ws1.merge_cells(f"A2:{get_column_letter(len(columns))}2")
    projekt = requirements.get("projekt", "")
    summary = matching["summary"]
    total = summary["total_positions"]
    matched_cnt = summary["matched_count"]
    partial_cnt = summary["partial_count"]
    unmatch_cnt = summary["unmatched_count"]
    ws1["A2"] = (
        f"{projekt}  |  {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  "
        f"{total} Positionen:  {matched_cnt} machbar,  {partial_cnt} teilweise,  {unmatch_cnt} nicht machbar"
    )
    ws1["A2"].font = subtitle_font
    ws1.row_dimensions[2].height = 20

    # Empty row 3
    ws1.row_dimensions[3].height = 6

    # Header row (row 4)
    HEADER_ROW = 4
    for col_idx, (header, _, _) in enumerate(columns, 1):
        cell = ws1.cell(row=HEADER_ROW, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_v
        cell.border = thin_border
    ws1.row_dimensions[HEADER_ROW].height = 26

    # Freeze panes: freeze header row so it stays visible when scrolling
    ws1.freeze_panes = "A5"

    # Auto-filter on header
    ws1.auto_filter.ref = f"A{HEADER_ROW}:{get_column_letter(len(columns))}{HEADER_ROW}"

    # ── Data rows ──────────────────────────────────
    all_positions = (
        matching.get("matched", [])
        + matching.get("partial", [])
        + matching.get("unmatched", [])
    )

    def _sort_key(entry):
        pos = entry.get("position", "")
        nums = re.findall(r"\d+", str(pos))
        return [int(n) for n in nums] if nums else [999999]

    all_positions.sort(key=_sort_key)

    row_num = HEADER_ROW + 1
    for i, entry in enumerate(all_positions):
        pos = entry.get("original_position", {})
        status = entry.get("status", "unmatched")

        # Status display
        if status == "matched":
            status_text = "MACHBAR"
            status_fill = green_fill
            s_font = status_font_ok
        elif status == "partial":
            status_text = "TEILWEISE"
            status_fill = yellow_fill
            s_font = status_font_warn
        else:
            status_text = "NICHT MACHBAR"
            status_fill = red_fill
            s_font = status_font_fail

        # Dimensions
        breite = pos.get("breite", "")
        hoehe = pos.get("hoehe", "")
        dim_text = ""
        if breite and hoehe:
            # Normalize to mm display
            b = breite
            h = hoehe
            try:
                b = float(b)
                h = float(h)
                if b < 20:
                    b = b * 1000
                elif b <= 400:
                    b = b * 10
                if h < 20:
                    h = h * 1000
                elif h <= 400:
                    h = h * 10
                dim_text = f"{int(b)} x {int(h)}"
            except (ValueError, TypeError):
                dim_text = f"{breite} x {hoehe}"

        # Hints / Gaps
        hints = _clean_reason(entry)

        # Türtyp from original data
        tuertyp = str(pos.get("tuertyp", pos.get("beschreibung", ""))).strip()

        values = [
            i + 1,                                              # Nr.
            str(entry.get("position", "")),                     # Tür-Nr.
            str(pos.get("raum", pos.get("besonderheiten", ""))),# Raum
            str(pos.get("geschoss", "")),                       # Geschoss
            tuertyp,                                            # Türtyp
            _get_product_name(entry),                           # FTAG Produkt
            str(entry.get("category", "")),                     # Kategorie
            dim_text,                                           # B x H
            str(pos.get("brandschutz", "") or ""),              # Brandschutz
            str(pos.get("schallschutz", "") or ""),             # Schallschutz
            str(pos.get("einbruchschutz", "") or ""),           # Einbruchschutz
            status_text,                                        # Status
            hints,                                              # Hinweise
        ]

        str_values = [str(v) if v else "" for v in values]
        row_height = _auto_row_height(str_values, col_widths_list)

        row_fill = alt_row_fill if i % 2 == 1 else None

        for col_idx, val in enumerate(values, 1):
            cell = ws1.cell(row=row_num, column=col_idx, value=val)
            cell.font = normal_font
            cell.border = thin_border
            cell.alignment = columns[col_idx - 1][2]
            if row_fill:
                cell.fill = row_fill

        # Status cell special formatting
        sc = ws1.cell(row=row_num, column=12)
        sc.fill = status_fill
        sc.font = s_font
        sc.alignment = center_v

        ws1.row_dimensions[row_num].height = row_height
        row_num += 1

    # Summary row
    row_num += 1
    last_col = get_column_letter(len(columns))
    ws1.merge_cells(f"A{row_num}:{last_col}{row_num}")
    ws1.cell(row=row_num, column=1, value=(
        f"Zusammenfassung:  {matched_cnt} machbar  /  {partial_cnt} teilweise  /  "
        f"{unmatch_cnt} nicht machbar  (von {total} Positionen)  –  "
        f"Match-Rate: {summary.get('match_rate', 0)}%"
    )).font = bold_font
    ws1.cell(row=row_num, column=1).fill = PatternFill("solid", fgColor="E8EAF0")
    ws1.row_dimensions[row_num].height = 24

    # Update auto-filter range to include all data
    ws1.auto_filter.ref = f"A{HEADER_ROW}:{last_col}{row_num - 2}"

    # ── Sheet 2: GAP-Report ─────────────────────────
    ws2 = wb.create_sheet("GAP-Report")

    gap_columns = [
        ("Nr.",         5,   center_v),
        ("Tür-Nr.",    16,   left_center),
        ("Türtyp",     22,   left_center),
        ("Kategorie",  15,   left_center),
        ("B x H (mm)", 14,   center_v),
        ("Anforderung", 35,  left_top),
        ("Hinweis",    50,   left_top),
    ]
    gap_widths = [c[1] for c in gap_columns]

    for col_idx, (header, width, _) in enumerate(gap_columns, 1):
        col_letter = get_column_letter(col_idx)
        ws2.column_dimensions[col_letter].width = width

    # Title
    last_gap_col = get_column_letter(len(gap_columns))
    ws2.merge_cells(f"A1:{last_gap_col}1")
    ws2["A1"] = "GAP-Report - Nicht erfuellbare Anforderungen"
    ws2["A1"].font = title_font
    ws2.row_dimensions[1].height = 32

    ws2.merge_cells(f"A2:{last_gap_col}2")
    ws2["A2"] = f"{projekt}  |  {datetime.now().strftime('%d.%m.%Y')}"
    ws2["A2"].font = subtitle_font
    ws2.row_dimensions[2].height = 20
    ws2.row_dimensions[3].height = 6

    # Header
    GAP_HEADER_ROW = 4
    for col_idx, (header, _, _) in enumerate(gap_columns, 1):
        cell = ws2.cell(row=GAP_HEADER_ROW, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_v
        cell.border = thin_border
    ws2.row_dimensions[GAP_HEADER_ROW].height = 26

    ws2.freeze_panes = "A5"

    gap_row = GAP_HEADER_ROW + 1
    gap_num = 0

    for entry in all_positions:
        gap_items = entry.get("gap_items", [])
        if not gap_items and entry.get("status") != "unmatched":
            continue

        pos = entry.get("original_position", {})

        # Dimensions
        breite = pos.get("breite", "")
        hoehe = pos.get("hoehe", "")
        dim_text = ""
        if breite and hoehe:
            try:
                b, h = float(breite), float(hoehe)
                if b < 20: b *= 1000
                elif b <= 400: b *= 10
                if h < 20: h *= 1000
                elif h <= 400: h *= 10
                dim_text = f"{int(b)} x {int(h)}"
            except (ValueError, TypeError):
                dim_text = f"{breite} x {hoehe}"

        tuertyp = str(pos.get("tuertyp", pos.get("beschreibung", ""))).strip()
        anforderung_parts = []
        if pos.get("brandschutz"):
            anforderung_parts.append(f"Brandschutz: {pos['brandschutz']}")
        if pos.get("schallschutz"):
            anforderung_parts.append(f"Schallschutz: {pos['schallschutz']}")
        if pos.get("einbruchschutz"):
            anforderung_parts.append(f"Einbruchschutz: {pos['einbruchschutz']}")
        anforderung = "\n".join(anforderung_parts)

        hinweis = "\n".join(str(g) for g in gap_items)

        gap_num += 1
        values = [
            gap_num,
            str(entry.get("position", "")),
            tuertyp,
            str(entry.get("category", "")),
            dim_text,
            anforderung,
            hinweis,
        ]

        str_values = [str(v) if v else "" for v in values]
        row_height = _auto_row_height(str_values, gap_widths)

        for col_idx, val in enumerate(values, 1):
            cell = ws2.cell(row=gap_row, column=col_idx, value=val)
            cell.font = normal_font
            cell.border = thin_border
            cell.alignment = gap_columns[col_idx - 1][2]
            if gap_num % 2 == 0:
                cell.fill = alt_row_fill

        # Color the status indicator
        if entry.get("status") == "unmatched":
            ws2.cell(row=gap_row, column=1).fill = red_fill
        else:
            ws2.cell(row=gap_row, column=1).fill = yellow_fill

        ws2.row_dimensions[gap_row].height = row_height
        gap_row += 1

    if gap_num == 0:
        ws2.merge_cells(f"A5:{last_gap_col}5")
        ws2["A5"] = "Keine GAP-Positionen - alle Anforderungen erfuellbar!"
        ws2["A5"].font = Font(name="Calibri", size=12, bold=True, color="155724")
        ws2["A5"].fill = light_green
        ws2["A5"].alignment = center_v
        ws2.row_dimensions[5].height = 30

    # Summary
    gap_row += 1
    ws2.merge_cells(f"A{gap_row}:{last_gap_col}{gap_row}")
    ws2.cell(row=gap_row, column=1, value=(
        f"Total: {gap_num} GAP-Positionen von {total} Gesamtpositionen"
    )).font = bold_font
    ws2.cell(row=gap_row, column=1).fill = PatternFill("solid", fgColor="E8EAF0")
    ws2.row_dimensions[gap_row].height = 24

    ws2.auto_filter.ref = f"A{GAP_HEADER_ROW}:{last_gap_col}{gap_row - 2}"

    # Write to bytes
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
