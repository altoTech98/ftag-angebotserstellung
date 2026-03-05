"""
Code Agent – Claude-powered autonomous code modification via Telegram.

Receives natural language instructions, reads project files, calls Claude API
to generate code changes, and applies them after user confirmation.
"""

import os
import re
import json
import logging
import glob as glob_module

logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Key project files (always included as context)
CORE_FILES = [
    "backend/services/fast_matcher.py",
    "backend/services/result_generator.py",
    "backend/services/catalog_index.py",
    "backend/services/excel_parser.py",
    "backend/services/telegram_bot.py",
    "backend/services/agent_brain.py",
    "backend/routers/analyze.py",
    "backend/main.py",
    "frontend/app.js",
    "frontend/style.css",
    "frontend/index.html",
]

# Max file content to send to Claude (per file)
MAX_FILE_CHARS = 15000
# Max total context
MAX_TOTAL_CONTEXT = 80000


def process_code_request(instruction: str) -> dict:
    """
    Process a code change request.

    Returns:
        {
            "response": str,           # Summary for user
            "changes": list[dict],     # Proposed file changes
            "needs_confirmation": bool,
            "pending_action": dict,
        }
    """
    try:
        # Step 1: Find relevant files
        relevant_files = _find_relevant_files(instruction)

        # Step 2: Read file contents
        file_contents = _read_files(relevant_files)

        if not file_contents:
            return {
                "response": "Konnte keine relevanten Projektdateien finden.",
                "changes": [],
                "needs_confirmation": False,
            }

        # Step 3: Call Claude for changes
        changes = _call_claude_for_changes(instruction, file_contents)

        if not changes:
            return {
                "response": "Claude konnte keine Aenderungen vorschlagen. Bitte praezisiere deine Anweisung.",
                "changes": [],
                "needs_confirmation": False,
            }

        # Step 4: Build summary for user confirmation
        summary_lines = [f"Vorgeschlagene Aenderungen ({len(changes)} Dateien):\n"]
        for c in changes:
            action = c.get("action", "edit")
            path = c.get("file_path", "?")
            desc = c.get("description", "")
            if action == "create":
                summary_lines.append(f"  + NEU: {path}")
            elif action == "delete":
                summary_lines.append(f"  - LOESCHEN: {path}")
            else:
                summary_lines.append(f"  ~ AENDERN: {path}")
            if desc:
                summary_lines.append(f"    {desc}")

        summary_lines.append("\nMit 'ja' bestaetigen oder 'nein' abbrechen.")
        summary = "\n".join(summary_lines)

        return {
            "response": summary,
            "changes": changes,
            "needs_confirmation": True,
            "pending_action": {
                "type": "apply_code_changes",
                "changes": changes,
                "instruction": instruction,
            },
        }

    except Exception as e:
        logger.error(f"Code agent failed: {e}", exc_info=True)
        return {
            "response": f"Fehler beim Verarbeiten: {str(e)[:300]}",
            "changes": [],
            "needs_confirmation": False,
        }


def apply_changes(changes: list[dict]) -> str:
    """Apply confirmed code changes to files. Returns status message."""
    applied = []
    errors = []

    for c in changes:
        file_path = c.get("file_path", "")
        action = c.get("action", "edit")
        abs_path = os.path.join(PROJECT_ROOT, file_path)

        # Security: prevent path traversal (e.g. ../../etc/passwd)
        if not os.path.realpath(abs_path).startswith(os.path.realpath(PROJECT_ROOT)):
            errors.append(f"Sicherheitsfehler: Pfad ausserhalb des Projekts: {file_path}")
            continue

        try:
            if action == "create":
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(c.get("content", ""))
                applied.append(f"+ {file_path}")

            elif action == "delete":
                if os.path.exists(abs_path):
                    os.remove(abs_path)
                    applied.append(f"- {file_path}")

            elif action == "edit":
                if not os.path.exists(abs_path):
                    errors.append(f"Datei nicht gefunden: {file_path}")
                    continue

                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()

                old_text = c.get("old_text", "")
                new_text = c.get("new_text", "")

                if old_text and old_text in content:
                    content = content.replace(old_text, new_text, 1)
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    applied.append(f"~ {file_path}")
                elif not old_text and new_text:
                    # Full file rewrite
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(new_text)
                    applied.append(f"~ {file_path} (komplett)")
                else:
                    errors.append(f"Alter Text nicht gefunden in {file_path}")

        except Exception as e:
            errors.append(f"Fehler bei {file_path}: {str(e)[:100]}")

    result_lines = []
    if applied:
        result_lines.append(f"Angewendet ({len(applied)}):")
        result_lines.extend(f"  {a}" for a in applied)
    if errors:
        result_lines.append(f"\nFehler ({len(errors)}):")
        result_lines.extend(f"  {e}" for e in errors)

    if applied:
        result_lines.append("\nServer wird automatisch neu geladen (--reload).")

    return "\n".join(result_lines) if result_lines else "Keine Aenderungen angewendet."


def _find_relevant_files(instruction: str) -> list[str]:
    """Determine which project files are relevant for the instruction."""
    instruction_lower = instruction.lower()
    relevant = set()

    # Keyword → file mapping
    keyword_files = {
        ("matcher", "matching", "score", "threshold", "produkt match"):
            ["backend/services/fast_matcher.py"],
        ("katalog", "catalog", "index", "produkt"):
            ["backend/services/catalog_index.py"],
        ("excel", "result", "tuermatrix", "gap", "export"):
            ["backend/services/result_generator.py"],
        ("parser", "tuerliste", "parse", "upload"):
            ["backend/services/excel_parser.py"],
        ("frontend", "ui", "anzeige", "tabelle", "modal", "style", "css", "design"):
            ["frontend/app.js", "frontend/style.css", "frontend/index.html"],
        ("api", "route", "endpoint", "analyze", "server"):
            ["backend/routers/analyze.py", "backend/main.py"],
        ("telegram", "bot", "agent"):
            ["backend/services/telegram_bot.py", "backend/services/agent_brain.py"],
        ("offer", "angebot"):
            ["backend/services/local_llm.py"],
    }

    for keywords, files in keyword_files.items():
        if any(kw in instruction_lower for kw in keywords):
            relevant.update(files)

    # Check for explicit file paths in instruction
    file_pattern = re.findall(r'[\w/\\]+\.\w{2,4}', instruction)
    for fp in file_pattern:
        fp_normalized = fp.replace("\\", "/")
        if os.path.exists(os.path.join(PROJECT_ROOT, fp_normalized)):
            relevant.add(fp_normalized)

    # If nothing specific found, include the most common files
    if not relevant:
        relevant = set(CORE_FILES[:5])

    return list(relevant)


def _read_files(file_paths: list[str]) -> dict[str, str]:
    """Read file contents, respecting size limits."""
    contents = {}
    total_chars = 0

    for fp in file_paths:
        abs_path = os.path.join(PROJECT_ROOT, fp)
        if not os.path.exists(abs_path):
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + f"\n\n... (gekuerzt, {len(content)} Zeichen total)"
            if total_chars + len(content) > MAX_TOTAL_CONTEXT:
                break
            contents[fp] = content
            total_chars += len(content)
        except Exception as e:
            logger.warning(f"Could not read {fp}: {e}")

    return contents


def _get_project_structure() -> str:
    """Get a compact project structure overview."""
    lines = ["Projektstruktur:"]
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip hidden dirs, venv, node_modules, __pycache__
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("__pycache__", ".venv", "venv", "node_modules", ".git")]
        rel = os.path.relpath(root, PROJECT_ROOT).replace("\\", "/")
        if rel == ".":
            rel = ""
        for f in files:
            if f.endswith((".py", ".js", ".html", ".css", ".bat", ".txt")):
                path = f"{rel}/{f}" if rel else f
                lines.append(f"  {path}")
    return "\n".join(lines[:50])


def _call_claude_for_changes(instruction: str, file_contents: dict[str, str]) -> list[dict]:
    """Call Claude API to generate code changes."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic SDK not installed")
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # Build file context
    files_block = ""
    for path, content in file_contents.items():
        files_block += f"\n\n### DATEI: {path}\n```\n{content}\n```"

    structure = _get_project_structure()

    system_prompt = f"""Du bist ein erfahrener Python/JavaScript-Entwickler fuer die Frank Tueren AG Anwendung.
Das Projekt ist eine FastAPI-basierte Webanwendung fuer KI-gestuetzte Angebotserstellung (Tueren).

{structure}

## AUFGABE
Der User gibt eine Anweisung zur Code-Aenderung. Analysiere die relevanten Dateien und
erstelle praezise Aenderungen.

## REGELN
- Aendere NUR was noetig ist, keine unnoetige Refaktorisierung
- Behalte den bestehenden Code-Stil bei
- Gib fuer Edits den EXAKTEN alten Text an (muss eindeutig im File vorkommen)
- Teste mental ob die Aenderung funktioniert
- Verwende keine Emojis im Code

## ANTWORTFORMAT
Antworte NUR mit einem JSON-Array von Aenderungen:
```json
[
  {{
    "file_path": "backend/services/fast_matcher.py",
    "action": "edit",
    "description": "Schwellwert von 60 auf 70 erhoehen",
    "old_text": "MATCH_THRESHOLD = 60",
    "new_text": "MATCH_THRESHOLD = 70"
  }},
  {{
    "file_path": "backend/services/new_file.py",
    "action": "create",
    "description": "Neue Hilfsfunktion",
    "content": "def helper():\\n    pass"
  }}
]
```

Actions: "edit" (old_text -> new_text), "create" (neues File), "delete" (File loeschen)
Fuer "edit": old_text muss ein EXAKTER, EINDEUTIGER Ausschnitt aus der Datei sein.
Wenn ein groesserer Block geaendert wird, gib genug Kontext damit old_text eindeutig ist."""

    user_message = f"""## ANWEISUNG
{instruction}

## RELEVANTE DATEIEN
{files_block}

Erstelle die noeötigen Code-Aenderungen als JSON-Array."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=120.0,
        )

        response_text = message.content[0].text.strip()

        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1].strip()

        changes = json.loads(response_text)
        if not isinstance(changes, list):
            changes = [changes]

        # Validate changes
        valid_changes = []
        for c in changes:
            if not c.get("file_path"):
                continue
            action = c.get("action", "edit")
            if action == "edit" and not c.get("old_text") and not c.get("new_text"):
                continue
            if action == "create" and not c.get("content"):
                continue
            valid_changes.append(c)

        logger.info(f"Claude proposed {len(valid_changes)} code changes")
        return valid_changes

    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return []
