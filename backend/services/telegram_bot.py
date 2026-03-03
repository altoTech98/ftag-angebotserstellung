"""
Telegram Bot Agent – Autonomer KI-Assistent fuer Frank Tueren AG.

Laeuft neben FastAPI im selben Prozess. Empfaengt Dateien und Nachrichten
via Telegram, fuehrt Analysen durch und sendet Ergebnisse zurueck.
"""

import os
import io
import logging
import asyncio
import functools
from typing import Optional

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_app: Optional[Application] = None


# ─── Auth ────────────────────────────────────────────────────

def authorized_only(func):
    """Only allow the configured TELEGRAM_CHAT_ID."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
            logger.warning(f"Unauthorized Telegram access from chat_id={chat_id}")
            return
        return await func(update, context)
    return wrapper


# ─── Command Handlers ───────────────────────────────────────

@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "FTAG Full Agent\n\n"
        "Schnell-Befehle:\n"
        "/status - System-Status\n"
        "/katalog - Produktkatalog\n"
        "/history - Letzte Analysen\n"
        "/clear - Konversation zuruecksetzen\n\n"
        "Voller Zugriff:\n"
        "- Shell-Befehle ausfuehren\n"
        "- Dateien lesen/schreiben/bearbeiten\n"
        "- Git (status, commit, push, ...)\n"
        "- Code aendern und deployen\n"
        "- Excel/PDF Dateien analysieren\n\n"
        "Schreib einfach was du brauchst."
    )


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.agent_brain import _action_status
    result = _action_status()
    await update.message.reply_text(result["response"])


@authorized_only
async def cmd_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.agent_brain import _action_catalog_info
    result = _action_catalog_info()
    await update.message.reply_text(result["response"])


@authorized_only
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.agent_brain import _action_history
    result = _action_history()
    await update.message.reply_text(result["response"])


# ─── Document Handler (Core Feature) ────────────────────────

@authorized_only
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded Excel/PDF/Word files."""
    doc = update.message.document
    filename = doc.file_name or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    supported = {".xlsx", ".xls", ".pdf", ".docx"}
    if ext not in supported:
        await update.message.reply_text(
            f"Dateityp '{ext}' nicht unterstuetzt.\n"
            f"Bitte Excel (.xlsx) oder PDF senden."
        )
        return

    await update.message.reply_text(
        f"Datei empfangen: {filename}\n"
        f"Analyse wird gestartet..."
    )

    # Download file bytes
    file = await doc.get_file()
    file_bytes = await file.download_as_bytearray()
    content = bytes(file_bytes)

    # Run analysis in background
    asyncio.create_task(
        _analyze_and_report(
            update.effective_chat.id, content, filename, ext, context.bot
        )
    )


async def _analyze_and_report(
    chat_id: int,
    content: bytes,
    filename: str,
    ext: str,
    bot: Bot,
):
    """Run analysis pipeline and send results via Telegram."""
    loop = asyncio.get_event_loop()

    try:
        if ext in (".xlsx", ".xls"):
            await _analyze_excel(chat_id, content, filename, bot, loop)
        else:
            await _analyze_document(chat_id, content, filename, ext, bot, loop)

    except Exception as e:
        logger.error(f"Telegram analysis failed: {e}", exc_info=True)
        await bot.send_message(chat_id, f"Fehler bei der Analyse:\n{str(e)[:500]}")


async def _analyze_excel(
    chat_id: int,
    content: bytes,
    filename: str,
    bot: Bot,
    loop: asyncio.AbstractEventLoop,
):
    """Excel Tuerliste analysis pipeline."""
    from services.excel_parser import parse_tuerliste_bytes
    from services.fast_matcher import match_all as fast_match_all
    from services.result_generator import generate_result_excel
    from services.history_store import save_analysis

    # Step 1: Parse
    await bot.send_message(chat_id, "Excel wird geparst...")
    parsed = await loop.run_in_executor(None, parse_tuerliste_bytes, content)
    doors = parsed["doors"]

    if not doors:
        await bot.send_message(chat_id, "Keine Tuerpositionen in der Datei gefunden.")
        return

    await bot.send_message(chat_id, f"{len(doors)} Positionen gefunden. Matching laeuft...")

    # Step 2: Prepare positions
    positions = []
    for d in doors:
        pos = {k: v for k, v in d.items() if k != "_raw_row" and v is not None}
        positions.append(pos)

    requirements = {
        "projekt": "",
        "auftraggeber": "",
        "positionen": positions,
        "gesamtanzahl_tueren": sum(d.get("menge", 1) for d in positions),
        "hinweise": "",
    }

    # Step 3: Match
    match_result = await loop.run_in_executor(None, fast_match_all, positions)

    # Step 4: Summary
    s = match_result["summary"]
    summary = (
        f"Analyse abgeschlossen: {filename}\n\n"
        f"Total: {s['total_positions']} Positionen\n"
        f"Machbar: {s['matched_count']}\n"
        f"Teilweise: {s['partial_count']}\n"
        f"Nicht machbar: {s['unmatched_count']}\n"
        f"Match-Rate: {s['match_rate']}%"
    )
    await bot.send_message(chat_id, summary)

    # Step 5: Generate Excel
    await bot.send_message(chat_id, "Excel wird generiert...")
    result_id = os.path.splitext(filename)[0][:20]
    xlsx_bytes = await loop.run_in_executor(
        None, generate_result_excel, match_result, requirements, result_id
    )

    # Step 6: Send file
    bio = io.BytesIO(xlsx_bytes)
    bio.name = f"FTAG_Machbarkeit_{os.path.splitext(filename)[0]}.xlsx"
    await bot.send_document(
        chat_id=chat_id,
        document=bio,
        caption="Machbarkeitsanalyse + GAP-Report",
    )

    # Step 7: Save to history
    try:
        save_analysis(
            file_id=filename, filename=filename,
            requirements=requirements, matching=match_result,
        )
    except Exception as e:
        logger.warning(f"Could not save to history: {e}")


async def _analyze_document(
    chat_id: int,
    content: bytes,
    filename: str,
    ext: str,
    bot: Bot,
    loop: asyncio.AbstractEventLoop,
):
    """PDF/Word document analysis pipeline."""
    from services.document_parser import parse_document_bytes
    from services.local_llm import extract_requirements_from_text
    from services.fast_matcher import match_all as fast_match_all
    from services.result_generator import generate_result_excel
    from services.history_store import save_analysis

    # Step 1: Parse text
    await bot.send_message(chat_id, "Dokument wird gelesen...")
    text = await loop.run_in_executor(None, parse_document_bytes, content, ext)

    if not text or not text.strip():
        await bot.send_message(chat_id, "Dokument ist leer oder nicht lesbar.")
        return

    await bot.send_message(chat_id, f"Text extrahiert ({len(text)} Zeichen). KI-Analyse...")

    # Step 2: Extract requirements
    requirements = await loop.run_in_executor(
        None, extract_requirements_from_text, text
    )
    positions = requirements.get("positionen", [])

    if not positions:
        await bot.send_message(chat_id, "Keine Tuerpositionen im Dokument erkannt.")
        return

    await bot.send_message(chat_id, f"{len(positions)} Positionen erkannt. Matching...")

    # Step 3: Match
    match_result = await loop.run_in_executor(None, fast_match_all, positions)

    # Step 4: Summary
    s = match_result["summary"]
    summary = (
        f"Analyse abgeschlossen: {filename}\n\n"
        f"Total: {s['total_positions']} Positionen\n"
        f"Machbar: {s['matched_count']}\n"
        f"Teilweise: {s['partial_count']}\n"
        f"Nicht machbar: {s['unmatched_count']}\n"
        f"Match-Rate: {s['match_rate']}%"
    )
    await bot.send_message(chat_id, summary)

    # Step 5: Generate Excel
    result_id = os.path.splitext(filename)[0][:20]
    xlsx_bytes = await loop.run_in_executor(
        None, generate_result_excel, match_result, requirements, result_id
    )

    # Step 6: Send file
    bio = io.BytesIO(xlsx_bytes)
    bio.name = f"FTAG_Machbarkeit_{os.path.splitext(filename)[0]}.xlsx"
    await bot.send_document(
        chat_id=chat_id,
        document=bio,
        caption="Machbarkeitsanalyse + GAP-Report",
    )

    # Step 7: Save history
    try:
        save_analysis(
            file_id=filename, filename=filename,
            requirements=requirements, matching=match_result,
        )
    except Exception as e:
        logger.warning(f"Could not save to history: {e}")


# ─── Text Message Handler (Full Agent) ──────────────────────

@authorized_only
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-text messages via Claude agentic loop."""
    text = update.message.text.strip()
    if not text:
        return

    logger.info(f"Telegram text received: '{text[:100]}'")
    chat_id = str(update.effective_chat.id)

    # Process via full agent in background
    asyncio.create_task(
        _process_via_agent(chat_id, text, context.bot)
    )


async def _process_via_agent(chat_id: str, instruction: str, bot: Bot):
    """Process instruction via the full Claude agent and reply."""
    from services.full_agent import process_message

    chat_id_int = int(chat_id)

    # Send typing indicator
    try:
        await bot.send_chat_action(chat_id_int, "typing")
    except Exception:
        pass

    # Status callback for progress updates
    async def on_status(status_text: str):
        try:
            await bot.send_chat_action(chat_id_int, "typing")
        except Exception:
            pass

    try:
        response = await process_message(chat_id, instruction, on_status=on_status)
        await _send_long_message(bot, chat_id_int, response)
    except Exception as e:
        logger.error(f"Agent processing failed: {e}", exc_info=True)
        await bot.send_message(chat_id_int, f"Fehler: {str(e)[:300]}")


async def _send_long_message(bot: Bot, chat_id: int, text: str, max_len: int = 4000):
    """Send a message, splitting into multiple if needed."""
    if not text:
        text = "(Keine Antwort)"
    if len(text) <= max_len:
        await bot.send_message(chat_id, text)
        return

    # Split on newlines
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line[:max_len]
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(0.3)
        await bot.send_message(chat_id, chunk)


# ─── Clear Command ───────────────────────────────────────────

@authorized_only
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history."""
    from services.full_agent import clear_conversation
    chat_id = str(update.effective_chat.id)
    clear_conversation(chat_id)
    await update.message.reply_text("Konversation zurueckgesetzt.")


# ─── Lifecycle ───────────────────────────────────────────────

async def start_bot():
    """Initialize and start the Telegram bot. Called from FastAPI lifespan."""
    global _app

    if not TELEGRAM_BOT_TOKEN:
        logger.info("TELEGRAM_BOT_TOKEN not set – Telegram bot disabled.")
        return

    if not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set – bot will accept all users!")

    _app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers (order matters: commands first, then documents, then text)
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("help", cmd_start))
    _app.add_handler(CommandHandler("status", cmd_status))
    _app.add_handler(CommandHandler("katalog", cmd_katalog))
    _app.add_handler(CommandHandler("history", cmd_history))
    _app.add_handler(CommandHandler("clear", cmd_clear))
    _app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Start polling
    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)

    logger.info("Telegram bot started (polling mode)")

    # Startup notification
    if TELEGRAM_CHAT_ID:
        try:
            await _app.bot.send_message(
                int(TELEGRAM_CHAT_ID),
                "FTAG Agent gestartet.\n"
                "Voller Zugriff: Shell, Dateien, Git.\n"
                "Schreib einfach was du brauchst.\n"
                "/clear - Konversation zuruecksetzen"
            )
        except Exception as e:
            logger.warning(f"Could not send startup message: {e}")


async def stop_bot():
    """Gracefully stop the Telegram bot. Called from FastAPI lifespan."""
    global _app
    if _app is None:
        return

    try:
        if _app.updater and _app.updater.running:
            await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()
        logger.info("Telegram bot stopped")
    except Exception as e:
        logger.warning(f"Error stopping Telegram bot: {e}")
    _app = None


# ─── Proactive Messaging ────────────────────────────────────

async def send_message(text: str):
    """Send a proactive message to the authorized user."""
    if _app and TELEGRAM_CHAT_ID:
        try:
            await _app.bot.send_message(int(TELEGRAM_CHAT_ID), text[:4096])
        except Exception as e:
            logger.warning(f"Failed to send Telegram message: {e}")


async def send_document(file_bytes: bytes, filename: str, caption: str = ""):
    """Send a file to the authorized user."""
    if _app and TELEGRAM_CHAT_ID:
        try:
            bio = io.BytesIO(file_bytes)
            bio.name = filename
            await _app.bot.send_document(
                chat_id=int(TELEGRAM_CHAT_ID),
                document=bio,
                caption=caption[:1024] if caption else None,
            )
        except Exception as e:
            logger.warning(f"Failed to send Telegram document: {e}")
