"""
Full Agent – Claude API Tool-Use Agentic Loop fuer Telegram.

Ersetzt agent_brain + code_agent mit einem echten Claude-Agenten
der Shell-Befehle, Dateien, Git und mehr ausfuehren kann.
"""

import os
import re
import subprocess
import glob as glob_module
import fnmatch
import logging
import asyncio
from typing import Optional, Callable

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV_PYTHON = os.path.join(PROJECT_ROOT, "backend", ".venv", "Scripts", "python.exe")
VENV_PIP = os.path.join(PROJECT_ROOT, "backend", ".venv", "Scripts", "pip.exe")

MAX_TOOL_RESULT_CHARS = 12000
MAX_HISTORY_MESSAGES = 40
MAX_ITERATIONS = 25

# In-memory conversation store per chat_id
_conversations: dict[str, list[dict]] = {}

SYSTEM_PROMPT = (
    "Du bist ein vollstaendiger Entwicklungs-Agent fuer das Frank Tueren AG Projekt.\n"
    "Du laeuft auf einem Windows 10 PC. Das Projekt liegt unter C:\\Users\\ALI\\Desktop\\ClaudeCodeTest.\n\n"
    "Projektstruktur:\n"
    "- backend/ - Python FastAPI Backend (main.py, routers/, services/)\n"
    "- frontend/ - Vanilla HTML/CSS/JS (app.js, index.html, style.css)\n"
    "- data/ - Produktkatalog (produktuebersicht.xlsx), Feedback, History\n"
    "- uploads/ - Hochgeladene Dateien\n"
    "- outputs/ - Generierte Angebote/Reports\n\n"
    "Tech Stack: Python 3.12 + FastAPI, anthropic SDK, openpyxl, pdfplumber, python-docx\n"
    "Venv: backend/.venv (Windows), Python: backend/.venv/Scripts/python.exe\n"
    "Server: uvicorn mit --reload (Aenderungen an .py Files werden automatisch geladen)\n"
    "Git Remote: origin -> GitHub\n\n"
    "REGELN:\n"
    "- Antworte auf Deutsch\n"
    "- Lies Dateien ZUERST bevor du sie bearbeitest\n"
    "- Fuer pip/python: nutze den venv-Pfad oder execute_shell\n"
    "- Git-Befehle direkt ausfuehren\n"
    "- Sei praezise und kurz in deinen Antworten\n"
    "- Wenn eine Aufgabe mehrere Schritte braucht, fuehre ALLE Schritte aus\n"
    "- Bei Fehlern: analysiere und versuche zu beheben\n"
    "- Keine Emojis verwenden"
)

# ─── Tool Definitions ────────────────────────────────────────

TOOLS = [
    {
        "name": "execute_shell",
        "description": (
            "Execute a shell command on the Windows server (Git Bash available). "
            "Working directory is the project root. "
            "Use for: running scripts, pip install, checking processes, etc. "
            "Do NOT use for simple file reads/writes (use dedicated tools). "
            "For pip/python commands, the venv is automatically used."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30, max 120)",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file. Path is relative to project root. "
            "Returns file contents as text. Use max_lines and offset for large files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path relative to project root (e.g. 'backend/main.py')",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Max lines to return (0 = all)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start from (0-based)",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file. Creates file and parent dirs if needed. "
            "Overwrites existing content. Path relative to project root."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path relative to project root",
                },
                "content": {
                    "type": "string",
                    "description": "Full content to write",
                },
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Targeted edit: replace exact text in a file. "
            "old_text must match EXACTLY (including whitespace). "
            "Use read_file first to see current content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path relative to project root",
                },
                "old_text": {
                    "type": "string",
                    "description": "Exact text to find (must be unique in file)",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text",
                },
            },
            "required": ["file_path", "old_text", "new_text"],
        },
    },
    {
        "name": "list_directory",
        "description": (
            "List files and directories. Supports glob patterns. "
            "Filters out .venv, __pycache__, .git, node_modules."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to project root (default: '.')",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter (e.g. '*.py', '**/*.js')",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List subdirectories recursively",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_files",
        "description": (
            "Search for a regex pattern in file contents. "
            "Returns matching lines with file paths and line numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: '.')",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob to filter files (e.g. '*.py')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results (default 50)",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "git_command",
        "description": (
            "Execute a git command in the project repository. "
            "Supports: status, add, commit, push, pull, log, diff, branch, checkout, stash, etc. "
            "For commit use -m flag. Credentials are configured in git config."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "args": {
                    "type": "string",
                    "description": "Git arguments (e.g. 'status', 'add .', 'commit -m \"msg\"', 'push origin master')",
                },
            },
            "required": ["args"],
        },
    },
]


# ─── Path Security ───────────────────────────────────────────

def _resolve_path(relative_path: str) -> str:
    """Resolve relative path to absolute, ensuring within PROJECT_ROOT."""
    relative_path = relative_path.replace("/", os.sep).replace("\\", os.sep)
    relative_path = relative_path.lstrip(os.sep)
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, relative_path))
    if not abs_path.startswith(os.path.normpath(PROJECT_ROOT)):
        raise ValueError(f"Zugriff verweigert: Pfad ausserhalb Projekt")
    return abs_path


def _truncate(text: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Truncate long text keeping start and end."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n\n... ({len(text) - max_chars} Zeichen gekuerzt) ...\n\n" + text[-half:]


# ─── Tool Execution Functions ────────────────────────────────

def tool_execute_shell(command: str, timeout_seconds: int = 30) -> str:
    timeout_seconds = max(5, min(timeout_seconds or 30, 120))

    # Auto-use venv for pip/python
    cmd = command
    if cmd.strip().startswith("pip "):
        cmd = f'"{VENV_PIP}" {cmd.strip()[4:]}'
    elif cmd.strip().startswith("python "):
        cmd = f'"{VENV_PYTHON}" {cmd.strip()[7:]}'

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout_seconds, cwd=PROJECT_ROOT,
            encoding="utf-8", errors="replace",
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- STDERR ---\n" + result.stderr) if output else result.stderr
        if result.returncode != 0:
            output += f"\n(Exit Code: {result.returncode})"
        return _truncate(output) if output else "(Kein Output)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: Befehl nach {timeout_seconds}s abgebrochen."
    except Exception as e:
        return f"FEHLER: {e}"


def tool_read_file(file_path: str, max_lines: int = 0, offset: int = 0) -> str:
    abs_path = _resolve_path(file_path)
    if not os.path.exists(abs_path):
        return f"FEHLER: Datei nicht gefunden: {file_path}"
    if not os.path.isfile(abs_path):
        return f"FEHLER: Ist ein Verzeichnis: {file_path}"
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        if offset and offset > 0:
            lines = lines[offset:]
        if max_lines and max_lines > 0:
            lines = lines[:max_lines]
        content = "".join(lines)
        header = f"--- {file_path} ({total} Zeilen) ---\n"
        return header + _truncate(content)
    except Exception as e:
        return f"FEHLER: {e}"


def tool_write_file(file_path: str, content: str) -> str:
    abs_path = _resolve_path(file_path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return f"Datei geschrieben: {file_path} ({len(content)} Zeichen)"
    except Exception as e:
        return f"FEHLER: {e}"


def tool_edit_file(file_path: str, old_text: str, new_text: str) -> str:
    abs_path = _resolve_path(file_path)
    if not os.path.exists(abs_path):
        return f"FEHLER: Datei nicht gefunden: {file_path}"
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        if old_text not in content:
            return f"FEHLER: Text nicht gefunden in {file_path}. Lies die Datei zuerst mit read_file."
        count = content.count(old_text)
        if count > 1:
            return f"WARNUNG: Text kommt {count}x vor. Verwende einen eindeutigeren Textblock."
        content = content.replace(old_text, new_text, 1)
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return f"Datei bearbeitet: {file_path} (1 Stelle geaendert)"
    except Exception as e:
        return f"FEHLER: {e}"


_SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}


def tool_list_directory(path: str = ".", pattern: str = None, recursive: bool = False) -> str:
    abs_path = _resolve_path(path or ".")
    if not os.path.exists(abs_path):
        return f"FEHLER: Verzeichnis nicht gefunden: {path}"
    try:
        if pattern:
            if recursive:
                search = os.path.join(abs_path, "**", pattern)
            else:
                search = os.path.join(abs_path, pattern)
            matches = glob_module.glob(search, recursive=recursive)
            matches = [m for m in matches if not any(s in m for s in _SKIP_DIRS)]
            lines = []
            for m in sorted(matches)[:100]:
                rel = os.path.relpath(m, PROJECT_ROOT).replace("\\", "/")
                if os.path.isfile(m):
                    lines.append(f"  {rel} ({os.path.getsize(m)} bytes)")
                else:
                    lines.append(f"  {rel}/")
            header = f"{len(matches)} Treffer"
            if len(matches) > 100:
                header += " (erste 100)"
            return header + ":\n" + "\n".join(lines)
        else:
            entries = sorted(os.listdir(abs_path))
            entries = [e for e in entries if e not in _SKIP_DIRS]
            lines = []
            for entry in entries:
                full = os.path.join(abs_path, entry)
                if os.path.isdir(full):
                    lines.append(f"  {entry}/")
                else:
                    lines.append(f"  {entry} ({os.path.getsize(full)} bytes)")
            return f"Verzeichnis {path or '.'} ({len(entries)} Eintraege):\n" + "\n".join(lines)
    except Exception as e:
        return f"FEHLER: {e}"


def tool_search_files(pattern: str, path: str = ".", file_pattern: str = None, max_results: int = 50) -> str:
    abs_path = _resolve_path(path or ".")
    max_results = min(max_results or 50, 100)
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"FEHLER: Ungueltiges Regex: {e}"

    results = []
    for root, dirs, files in os.walk(abs_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if file_pattern and not fnmatch.fnmatch(fname, file_pattern):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, PROJECT_ROOT).replace("\\", "/")
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"  {rel}:{i}: {line.rstrip()[:120]}")
                            if len(results) >= max_results:
                                break
            except (PermissionError, OSError):
                continue
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break

    if not results:
        return f"Keine Treffer fuer '{pattern}'"
    return f"{len(results)} Treffer fuer '{pattern}':\n" + "\n".join(results)


def tool_git_command(args: str) -> str:
    dangerous = ["filter-branch", "reflog expire", "gc --prune"]
    if any(d in args.lower() for d in dangerous):
        return f"FEHLER: Befehl nicht erlaubt: git {args}"
    try:
        result = subprocess.run(
            f"git {args}", shell=True, capture_output=True, text=True,
            timeout=60, cwd=PROJECT_ROOT, encoding="utf-8", errors="replace",
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" + result.stderr) if output else result.stderr
        if result.returncode != 0 and not output:
            output = f"Git Fehler (Exit Code: {result.returncode})"
        return _truncate(output) if output else "(Kein Output)"
    except subprocess.TimeoutExpired:
        return "TIMEOUT: Git-Befehl nach 60s abgebrochen."
    except Exception as e:
        return f"FEHLER: {e}"


# ─── Tool Dispatcher ────────────────────────────────────────

_TOOL_FUNCTIONS = {
    "execute_shell": lambda p: tool_execute_shell(p["command"], p.get("timeout_seconds", 30)),
    "read_file": lambda p: tool_read_file(p["file_path"], p.get("max_lines", 0), p.get("offset", 0)),
    "write_file": lambda p: tool_write_file(p["file_path"], p["content"]),
    "edit_file": lambda p: tool_edit_file(p["file_path"], p["old_text"], p["new_text"]),
    "list_directory": lambda p: tool_list_directory(p.get("path", "."), p.get("pattern"), p.get("recursive", False)),
    "search_files": lambda p: tool_search_files(p["pattern"], p.get("path", "."), p.get("file_pattern"), p.get("max_results", 50)),
    "git_command": lambda p: tool_git_command(p["args"]),
}


def _execute_tool(name: str, params: dict) -> str:
    func = _TOOL_FUNCTIONS.get(name)
    if not func:
        return f"FEHLER: Unbekanntes Tool: {name}"
    try:
        return func(params)
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        return f"FEHLER bei {name}: {str(e)[:500]}"


# ─── Conversation Management ────────────────────────────────

def _get_conversation(chat_id: str) -> list[dict]:
    if chat_id not in _conversations:
        _conversations[chat_id] = []
    conv = _conversations[chat_id]
    if len(conv) > MAX_HISTORY_MESSAGES:
        _conversations[chat_id] = conv[-MAX_HISTORY_MESSAGES:]
    return _conversations[chat_id]


def clear_conversation(chat_id: str):
    _conversations.pop(chat_id, None)


# ─── Status Messages ────────────────────────────────────────

def _tool_status(name: str, params: dict) -> str:
    if name == "execute_shell":
        return f"Shell: {params.get('command', '')[:50]}..."
    if name == "read_file":
        return f"Lese: {params.get('file_path', '')}"
    if name == "write_file":
        return f"Schreibe: {params.get('file_path', '')}"
    if name == "edit_file":
        return f"Bearbeite: {params.get('file_path', '')}"
    if name == "list_directory":
        return f"Liste: {params.get('path', '.')}"
    if name == "search_files":
        return f"Suche: {params.get('pattern', '')}"
    if name == "git_command":
        return f"Git: {params.get('args', '')}"
    return f"Tool: {name}"


# ─── Agentic Loop ────────────────────────────────────────────

# Use haiku for lower token cost and faster responses (30k tokens/min limit)
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-haiku-4-5-20251001")


def _ensure_valid_history(conversation: list[dict]):
    """
    Fix conversation history to ensure valid alternating user/assistant
    and that tool_results have matching tool_use blocks.
    Removes orphaned messages at the end if needed.
    """
    if not conversation:
        return

    # The conversation must end with a user message (for the next API call)
    # or be in a clean state. Remove trailing broken pairs.
    while conversation:
        last = conversation[-1]
        role = last.get("role", "")
        content = last.get("content", "")

        # If last message is assistant with tool_use but no following tool_result, remove it
        if role == "assistant" and isinstance(content, list):
            has_tool_use = any(
                isinstance(b, dict) and b.get("type") == "tool_use"
                for b in content
            )
            if has_tool_use:
                # Check if there's no matching tool_result after this
                conversation.pop()
                continue

        # If last is user with tool_results but previous isn't assistant with tool_use, remove
        if role == "user" and isinstance(content, list):
            has_tool_result = any(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            )
            if has_tool_result:
                conversation.pop()
                continue

        break

    # Ensure alternating roles (user, assistant, user, assistant...)
    cleaned = []
    for msg in conversation:
        if cleaned and cleaned[-1].get("role") == msg.get("role"):
            # Same role twice: keep the latest
            cleaned[-1] = msg
        else:
            cleaned.append(msg)

    conversation.clear()
    conversation.extend(cleaned)


async def process_message(
    chat_id: str,
    user_message: str,
    on_status: Optional[Callable] = None,
) -> str:
    """
    Process a user message through Claude agentic loop with tools.
    Returns final response text.
    """
    import anthropic
    import time

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "ANTHROPIC_API_KEY nicht gesetzt. Bitte Environment-Variable setzen."

    client = anthropic.Anthropic(api_key=api_key)
    conversation = _get_conversation(chat_id)

    # Fix any corruption from previous errors
    _ensure_valid_history(conversation)

    # Add user message
    conversation.append({"role": "user", "content": user_message})

    loop = asyncio.get_event_loop()

    for iteration in range(MAX_ITERATIONS):
        # Call Claude API with retry for rate limits
        response = None
        for retry in range(3):
            try:
                response = client.messages.create(
                    model=AGENT_MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=conversation,
                    timeout=120.0,
                )
                break
            except anthropic.RateLimitError as e:
                wait = (retry + 1) * 15  # 15s, 30s, 45s
                logger.warning(f"Rate limit hit, waiting {wait}s (retry {retry+1}/3)")
                if on_status:
                    try:
                        await on_status(f"Rate-Limit, warte {wait}s...")
                    except Exception:
                        pass
                await asyncio.sleep(wait)
            except anthropic.BadRequestError as e:
                # Conversation history corrupted — reset and retry
                logger.error(f"Bad request (resetting history): {e}")
                conversation.clear()
                conversation.append({"role": "user", "content": user_message})
                if retry < 2:
                    continue
                return f"API Fehler: {str(e)[:200]}\nKonversation wurde zurueckgesetzt."
            except Exception as e:
                logger.error(f"Claude API error: {e}")
                return f"Claude API Fehler: {str(e)[:300]}"

        if response is None:
            return "Rate-Limit erreicht. Bitte 1 Minute warten und nochmal versuchen."

        # Convert content blocks to serializable format
        content_list = []
        for block in response.content:
            if block.type == "text":
                content_list.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content_list.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        conversation.append({"role": "assistant", "content": content_list})

        if response.stop_reason == "end_turn":
            parts = [b.text for b in response.content if b.type == "text"]
            return "\n".join(parts) if parts else "Fertig."

        elif response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if on_status:
                        try:
                            await on_status(_tool_status(block.name, block.input))
                        except Exception:
                            pass

                    result = await loop.run_in_executor(
                        None, _execute_tool, block.name, block.input
                    )
                    logger.info(f"Tool {block.name}: {result[:80]}...")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            conversation.append({"role": "user", "content": tool_results})

        else:
            parts = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(parts) if parts else f"Stop: {response.stop_reason}"

    return "Max Iterationen (25) erreicht. Versuch es mit einem einfacheren Befehl."
