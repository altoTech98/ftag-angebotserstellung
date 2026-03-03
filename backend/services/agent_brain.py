"""
Agent Brain – KI-Entscheidungslogik fuer den Telegram Bot.

Interpretiert natuerliche Sprache, routet zu Aktionen, nutzt LLM fuer komplexe Fragen.
"""

import logging

logger = logging.getLogger(__name__)


def process_instruction(instruction: str) -> dict:
    """
    Process a natural language instruction and return a response.

    Returns dict with keys:
        response: str           - Text to send back
        action: str             - What action was taken
        needs_confirmation: bool - Whether user must confirm
        pending_action: dict    - Action to execute if confirmed
        file_bytes: bytes       - Optional file to send
        file_name: str          - Optional filename
    """
    text = instruction.lower().strip()

    # Quick keyword routing (no LLM needed)
    if any(kw in text for kw in ("status", "wie geht", "laeuft", "läuft")):
        return _action_status()

    if any(kw in text for kw in ("katalog", "sortiment", "kategorien")):
        return _action_catalog_info()

    if any(kw in text for kw in ("history", "letzte", "vergangene", "analysen")):
        return _action_history()

    if any(kw in text for kw in ("such", "find", "search", "produkt")):
        return _action_search_products(instruction)

    if any(kw in text for kw in ("hilfe", "help", "was kannst", "befehle")):
        return _action_help()

    # Code change request detection
    if _is_code_request(text):
        return _action_code_change(instruction)

    # Complex: use LLM
    return _llm_process(instruction)


def _action_help() -> dict:
    return {
        "response": (
            "Verfuegbare Befehle:\n"
            "/status - System-Status\n"
            "/katalog - Produktkatalog anzeigen\n"
            "/history - Letzte Analysen\n\n"
            "Oder einfach:\n"
            "- Excel/PDF Datei senden -> automatische Analyse\n"
            "- 'Suche EI60 Rahmentuere' -> Produktsuche\n"
            "- 'Status' -> Systeminfo\n"
            "- Beliebige Frage zu Tueren/Brandschutz\n\n"
            "Code-Aenderungen (braucht ANTHROPIC_API_KEY):\n"
            "- 'Aendere den Schwellwert auf 70'\n"
            "- 'Fuege eine neue Spalte hinzu'\n"
            "- 'Mach die Tabelle breiter'\n"
            "- 'Fix den Bug in der Suche'"
        ),
        "action": "help",
    }


def _action_status() -> dict:
    from services.catalog_index import get_catalog_index
    from services.memory_cache import text_cache, offer_cache
    from services.feedback_store import get_feedback_stats

    catalog = get_catalog_index()
    fb = get_feedback_stats()

    response = (
        f"System Status\n\n"
        f"Katalog: {len(catalog.main_products)} Produkte, "
        f"{len(catalog.main_category_names)} Kategorien\n"
        f"Feedback: {fb['total_feedback']} Eintraege "
        f"({fb['total_corrections']} Korrekturen)\n"
        f"Cache: {text_cache.stats()['items']} Texte, "
        f"{offer_cache.stats()['items']} Angebote"
    )

    try:
        from services.local_llm import check_ollama_status
        ollama = check_ollama_status()
        if ollama.get("available"):
            response += f"\nOllama: verfuegbar ({', '.join(ollama.get('models', []))})"
        else:
            response += "\nOllama: nicht verfuegbar"
    except Exception:
        response += "\nOllama: Status unbekannt"

    return {"response": response, "action": "show_status"}


def _action_catalog_info() -> dict:
    from services.catalog_index import get_catalog_index

    catalog = get_catalog_index()
    lines = [f"FTAG Produktkatalog ({len(catalog.main_products)} Hauptprodukte)\n"]

    for cat in catalog.main_category_names:
        products = catalog.by_category.get(cat, [])
        lines.append(f"  {cat}: {len(products)}")

    return {"response": "\n".join(lines), "action": "show_catalog"}


def _action_history() -> dict:
    from services.history_store import get_history_list

    entries = get_history_list()[:10]
    if not entries:
        return {"response": "Keine Analysen vorhanden.", "action": "show_history"}

    lines = ["Letzte Analysen:\n"]
    for e in entries:
        lines.append(
            f"{e['timestamp'][:16]} | {e['filename'][:30]}\n"
            f"  {e['positions_count']} Pos | "
            f"{e['matched_count']} OK | "
            f"{e['partial_count']} teil | "
            f"{e['unmatched_count']} nein | "
            f"{e['match_rate']}%"
        )

    return {"response": "\n".join(lines), "action": "show_history"}


def _action_search_products(instruction: str) -> dict:
    from services.catalog_index import get_catalog_index

    # Extract search term by removing command words
    import re
    terms = instruction.lower()
    terms = re.sub(
        r'\b(suche|such|finde|find|search|nach|fuer|für|produkt|produkte)\b',
        '', terms
    )
    search_term = " ".join(terms.split()).strip()

    if not search_term:
        return {
            "response": "Bitte Suchbegriff angeben, z.B. 'Suche EI60 Rahmentuere'",
            "action": "search_products",
        }

    catalog = get_catalog_index()

    # Normalize umlauts for matching
    def normalize(s):
        return (s.lower()
                .replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")
                .replace("ue", "ue").replace("ae", "ae").replace("oe", "oe"))

    search_normalized = normalize(search_term)
    search_words = search_normalized.split()

    results = []
    for p in catalog.main_products:
        text_normalized = normalize(p.compact_text)
        if all(w in text_normalized for w in search_words):
            results.append(p)

    if not results:
        return {
            "response": f"Keine Produkte gefunden fuer '{search_term}'.",
            "action": "search_products",
        }

    lines = [f"{len(results)} Produkte fuer '{search_term}':\n"]
    for p in results[:15]:
        lines.append(f"  [{p.row_index}] {p.compact_text[:80]}")
    if len(results) > 15:
        lines.append(f"  ... und {len(results) - 15} weitere")

    return {"response": "\n".join(lines), "action": "search_products"}


def _is_code_request(text: str) -> bool:
    """Detect if the instruction is a code change request."""
    import re
    # Action verbs that indicate code changes
    code_verbs = (
        r"\b(änder|aender|change|modify|fix|reparier|"
        r"füg|fueg|hinzufüg|hinzufueg|add|entfern|remove|lösch|loesch|"
        r"aktualisier|update|implementier|bau|schreib|erstell|"
        r"mach|verschieb|ersetz|replace|refactor|optimier|"
        r"anpass|umbau|erweit|verbess)"
    )
    # Code-related nouns
    code_nouns = (
        r"(code|datei|file|funktion|function|variable|klasse|class|"
        r"spalte|column|zeile|row|button|tabelle|table|"
        r"schwellwert|threshold|frontend|backend|css|html|"
        r"farbe|color|font|layout|design|api|endpoint|"
        r"import|modul|module|matching|matcher|parser|bot|agent|server)"
    )
    has_verb = bool(re.search(code_verbs, text, re.IGNORECASE))
    has_noun = bool(re.search(code_nouns, text, re.IGNORECASE))
    # Need both an action verb AND a code noun
    return has_verb and has_noun


def _action_code_change(instruction: str) -> dict:
    """Route code change requests to the code agent."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {
            "response": (
                "Code-Aenderungen brauchen die Claude API.\n"
                "Bitte ANTHROPIC_API_KEY setzen."
            ),
            "action": "code_change_blocked",
        }

    try:
        from services.code_agent import process_code_request
        return process_code_request(instruction)
    except Exception as e:
        logger.error(f"Code agent failed: {e}", exc_info=True)
        return {
            "response": f"Code-Agent Fehler: {str(e)[:300]}",
            "action": "code_change_error",
        }


def _llm_process(instruction: str) -> dict:
    """Use LLM for complex questions. Tries Ollama first, then Claude API."""
    system = (
        "Du bist ein KI-Assistent der Frank Tueren AG (Buochs NW, Schweiz). "
        "Du hilfst bei Fragen zu Tueren, Brandschutz, Schallschutz, "
        "Einbruchschutz und Ausschreibungen. "
        "Antworte kurz und praezise auf Deutsch."
    )

    # Try Ollama first
    try:
        from services.local_llm import _call_ollama
        response = _call_ollama(instruction, system=system, timeout=30.0)
        if response:
            return {"response": response[:4096], "action": "llm_answer"}
    except Exception as e:
        logger.info(f"Ollama not available: {e}")

    # Fallback: Claude API
    try:
        response = _call_claude_chat(instruction, system)
        if response:
            return {"response": response[:4096], "action": "llm_answer_claude"}
    except Exception as e:
        logger.warning(f"Claude chat failed: {e}")

    return {
        "response": (
            "Ich kann diese Anfrage gerade nicht verarbeiten.\n\n"
            "Verfuegbare Aktionen:\n"
            "/status - System-Status\n"
            "/katalog - Produktkatalog\n"
            "/history - Analyse-Verlauf\n"
            "Oder sende eine Excel/PDF Datei zur Analyse."
        ),
        "action": "fallback",
    }


def _call_claude_chat(instruction: str, system: str) -> str | None:
    """Call Claude API for general chat responses."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": instruction}],
            timeout=30.0,
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Claude API chat error: {e}")
        return None
