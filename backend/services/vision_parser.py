"""
Vision Parser – Claude Vision API for PDF analysis.

Renders PDF pages as images and sends them to Claude Vision
for structured extraction of door positions from architectural plans.

Fallback chain: pdfplumber text -> OCR -> Vision (this module).
Only "poor quality" pages (< 500 chars text) are sent to Vision.
Pages are batched in groups of 40 (no page limit).
"""

import io
import os
import re
import json
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum text length per page to consider "good" (skip Vision)
MIN_TEXT_QUALITY = 500
BATCH_SIZE = 40


def assess_page_quality(text: str, has_tables: bool = False) -> str:
    """Assess whether a page's extracted text is good enough or needs Vision."""
    if not text or not text.strip():
        return "poor"
    text_len = len(text.strip())
    # If page has tables but little text, it's likely a drawing/plan
    if has_tables and text_len < MIN_TEXT_QUALITY:
        return "poor"
    if text_len < MIN_TEXT_QUALITY:
        return "poor"
    return "good"


def create_batches(items: list, batch_size: int = BATCH_SIZE) -> list[list]:
    """Split items into batches of given size."""
    if not items:
        return []
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def render_pdf_pages(
    pdf_bytes: bytes,
    page_indices: list[int] = None,
    dpi: int = 150,
) -> list:
    """
    Render PDF pages to PIL Images.
    If page_indices is None, renders all pages.
    Returns list of PIL Image objects.
    """
    import pdfplumber
    from PIL import Image

    images = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        indices = page_indices if page_indices is not None else range(len(pdf.pages))
        for idx in indices:
            if idx >= len(pdf.pages):
                continue
            try:
                page = pdf.pages[idx]
                img = page.to_image(resolution=dpi)
                images.append(img.original)
            except Exception as e:
                logger.debug(f"[VISION] Failed to render page {idx + 1}: {e}")
                continue
    return images


def _image_to_base64(img, max_width: int = 1568) -> str:
    """Convert PIL Image to base64 JPEG, resizing if needed."""
    # Resize if too wide (Claude Vision max recommended: 1568px)
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def _build_vision_prompt(page_numbers: list[int]) -> str:
    """Build the system prompt for Claude Vision extraction."""
    return """Du analysierst Seiten aus einem Architektenplan / einer Ausschreibung fuer Tueren.

Extrahiere ALLE Tuerpositionen die du findest. Fuer jede Tuer extrahiere:
- tuer_nr: Positionsnummer (z.B. "T01.001", "1.01", "Pos 3")
- tuertyp: Tuertyp (z.B. "Stahltuer", "Holztuer", "Rahmentuere")
- brandschutz: Brandschutzklasse (z.B. "EI30", "T30", "EI60")
- schallschutz: Schallschutz (z.B. "Rw=32dB", "32dB")
- einbruchschutz: Einbruchschutz (z.B. "RC2", "WK3")
- breite: Breite in mm (z.B. 900)
- hoehe: Hoehe in mm (z.B. 2100)
- menge: Anzahl (default 1)
- verglasung: Verglasung falls vorhanden
- oberflaechenbehandlung: RAL-Farbe oder Oberflaeche
- zargentyp: Zargentyp falls angegeben
- besonderheiten: Weitere Besonderheiten

Antworte NUR mit einem JSON-Array. Keine Erklaerung, kein Markdown.
Wenn keine Tueren gefunden werden, antworte mit [].
Wenn Masse wie "900x2100" angegeben sind, trenne in breite=900, hoehe=2100.
"""


def extract_with_vision(
    pdf_bytes: bytes,
    poor_page_indices: list[int],
    on_progress: callable = None,
) -> list[dict]:
    """
    Send poor-quality pages to Claude Vision for structured extraction.

    Args:
        pdf_bytes: Raw PDF file bytes.
        poor_page_indices: 0-based page indices that need Vision analysis.
        on_progress: Optional callback(message: str) for progress updates.

    Returns:
        List of extracted door position dicts.
    """
    if not poor_page_indices:
        return []

    # Check if Claude is available
    from services.ai_service import get_ai_service
    ai = get_ai_service()
    ai._probe_engines()
    if ai._active_engine != "claude":
        logger.info("[VISION] Claude not available, skipping Vision extraction")
        return []

    client = ai._get_claude_client()
    if not client:
        return []

    from config import settings
    model = settings.CLAUDE_MODEL

    # Render only the poor pages
    if on_progress:
        on_progress(f"[VISION] Rendering {len(poor_page_indices)} Seiten als Bilder...")
    images = render_pdf_pages(pdf_bytes, page_indices=poor_page_indices)
    if not images:
        logger.warning("[VISION] No images rendered")
        return []

    # Batch and send
    batches = create_batches(list(zip(poor_page_indices, images)), batch_size=BATCH_SIZE)
    all_positions = []

    for batch_idx, batch in enumerate(batches):
        page_nums = [idx + 1 for idx, _ in batch]
        batch_images = [img for _, img in batch]

        if on_progress:
            on_progress(
                f"[VISION] Batch {batch_idx + 1}/{len(batches)}: "
                f"Analysiere Seiten {page_nums[0]}-{page_nums[-1]}..."
            )

        # Build message with images
        content = []
        for i, img in enumerate(batch_images):
            b64 = _image_to_base64(img)
            content.append({
                "type": "text",
                "text": f"Seite {page_nums[i]}:",
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            })

        content.append({
            "type": "text",
            "text": "Extrahiere alle Tuerpositionen aus diesen Seiten als JSON-Array.",
        })

        try:
            message = client.messages.create(
                model=model,
                max_tokens=8192,
                system=_build_vision_prompt(page_nums),
                messages=[{"role": "user", "content": content}],
                timeout=180.0,
            )

            # Extract text response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text = block.text.strip()
                    break

            if response_text:
                positions = parse_vision_response(response_text)
                all_positions.extend(positions)
                logger.info(
                    f"[VISION] Batch {batch_idx + 1}: {len(positions)} Positionen extrahiert"
                )

        except Exception as e:
            logger.warning(f"[VISION] Batch {batch_idx + 1} failed: {e}")
            continue

    logger.info(f"[VISION] Total: {len(all_positions)} Positionen aus {len(poor_page_indices)} Seiten")
    return all_positions


def parse_vision_response(response_text: str) -> list[dict]:
    """Parse Claude Vision JSON response into position dicts."""
    if not response_text:
        return []

    # Strip markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try JSON repair
        try:
            from services.local_llm import _repair_json
            data = _repair_json(text)
        except Exception:
            logger.warning(f"[VISION] Could not parse response: {text[:200]}")
            return []

    if isinstance(data, list):
        return [_normalize_position(p) for p in data if isinstance(p, dict)]
    if isinstance(data, dict) and "positionen" in data:
        return [_normalize_position(p) for p in data["positionen"] if isinstance(p, dict)]
    return []


def _normalize_position(pos: dict) -> dict:
    """Normalize a vision-extracted position to standard format."""
    result = {}
    for key in ("tuer_nr", "tuertyp", "brandschutz", "schallschutz",
                "einbruchschutz", "verglasung", "oberflaechenbehandlung",
                "zargentyp", "besonderheiten"):
        val = pos.get(key)
        if val and str(val).strip() and str(val).strip() not in ("-", "n/a", "keine"):
            result[key] = str(val).strip()

    for dim_key in ("breite", "hoehe"):
        val = pos.get(dim_key)
        if val is not None:
            try:
                result[dim_key] = int(float(val))
            except (ValueError, TypeError):
                pass

    menge = pos.get("menge", 1)
    try:
        result["menge"] = max(1, int(menge))
    except (ValueError, TypeError):
        result["menge"] = 1

    # Build beschreibung if not present
    if "beschreibung" not in result:
        parts = [result.get("tuertyp", "")]
        if result.get("brandschutz"):
            parts.append(result["brandschutz"])
        if result.get("breite") and result.get("hoehe"):
            parts.append(f"{result['breite']}x{result['hoehe']}mm")
        result["beschreibung"] = " ".join(p for p in parts if p)

    # Map tuer_nr -> position for compatibility
    if "tuer_nr" in result and "position" not in result:
        result["position"] = result["tuer_nr"]

    return result


def merge_extraction_results(
    text_pages: dict[int, str],
    vision_positions: list[dict],
) -> dict:
    """
    Merge pdfplumber text extraction with Vision-extracted positions.

    Args:
        text_pages: {page_number: extracted_text} from pdfplumber (good pages).
        vision_positions: Positions extracted by Claude Vision (poor pages).

    Returns:
        {"text": combined_text, "positions": vision_positions}
    """
    # Combine text from good pages
    combined_text = ""
    if text_pages:
        sorted_pages = sorted(text_pages.items())
        parts = [f"--- Seite {num} ---\n{text}" for num, text in sorted_pages]
        combined_text = "\n\n".join(parts)

    return {
        "text": combined_text,
        "positions": vision_positions,
    }


def analyze_pdf_hybrid(
    pdf_bytes: bytes,
    on_progress: callable = None,
) -> dict:
    """
    Hybrid PDF analysis: pdfplumber for text-rich pages, Vision for drawings/plans.

    Args:
        pdf_bytes: Raw PDF file bytes.
        on_progress: Optional progress callback.

    Returns:
        {
            "text": str,           # Combined text from good pages
            "positions": list,     # Structured positions from Vision
            "method": str,         # "text_only", "vision_only", "hybrid"
            "stats": dict,         # {"total_pages", "good_pages", "vision_pages"}
        }
    """
    import pdfplumber

    # Step 1: Extract text with pdfplumber and assess quality
    good_pages = {}  # page_num -> text
    poor_page_indices = []  # 0-based indices

    if on_progress:
        on_progress("[PDF] Analysiere Seitenqualitaet...")

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                has_tables = len(tables) > 0

                quality = assess_page_quality(text, has_tables)
                if quality == "good":
                    good_pages[idx + 1] = text
                    # Also add table text
                    for table in tables:
                        if table:
                            from services.document_parser import _table_to_text
                            table_text = _table_to_text(table)
                            if table_text:
                                good_pages[idx + 1] += f"\n[Tabelle]\n{table_text}"
                else:
                    poor_page_indices.append(idx)
            except Exception as e:
                logger.debug(f"[PDF] Page {idx + 1} extraction failed: {e}")
                poor_page_indices.append(idx)

    logger.info(
        f"[PDF] Quality check: {len(good_pages)} good, "
        f"{len(poor_page_indices)} poor out of {total_pages} pages"
    )

    # Step 2: Vision extraction for poor pages
    vision_positions = []
    if poor_page_indices:
        if on_progress:
            on_progress(
                f"[PDF] {len(poor_page_indices)} Seiten benoetigen Vision-Analyse..."
            )
        vision_positions = extract_with_vision(
            pdf_bytes, poor_page_indices, on_progress=on_progress
        )

    # Step 3: Determine method used
    if not poor_page_indices:
        method = "text_only"
    elif not good_pages:
        method = "vision_only"
    else:
        method = "hybrid"

    result = merge_extraction_results(good_pages, vision_positions)
    result["method"] = method
    result["stats"] = {
        "total_pages": total_pages,
        "good_pages": len(good_pages),
        "vision_pages": len(poor_page_indices),
        "positions_found": len(vision_positions),
    }

    return result
