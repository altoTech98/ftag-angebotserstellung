"""
AI Service – Unified AI abstraction with 3-tier failover.

Failover chain:
1. Claude API (Anthropic SDK) — highest quality, works everywhere
2. Ollama (local) — fast, free, offline-capable
3. None (caller handles regex fallback)

Usage:
    from services.ai_service import get_ai_service
    ai = get_ai_service()
    result = ai.call(prompt, system="...")  # returns str or None
    status = ai.get_status()               # {"engine": "claude", "available": True, ...}
"""

import os
import time
import logging
import httpx

logger = logging.getLogger(__name__)

# ─── Engine Constants ─────────────────────────────────────────
ENGINE_CLAUDE = "claude"
ENGINE_OLLAMA = "ollama"
ENGINE_REGEX = "regex"


class AIService:
    """
    Singleton AI service with automatic failover.
    Claude API -> Ollama -> None (regex handled by caller).
    """

    def __init__(self):
        from config import settings

        # Claude config
        self._anthropic_key = settings.ANTHROPIC_API_KEY
        self._claude_model = "claude-sonnet-4-6"
        self._claude_client = None

        # Ollama config
        self._ollama_base_url = settings.OLLAMA_URL
        self._ollama_model = settings.OLLAMA_MODEL
        self._ollama_generate_url = f"{self._ollama_base_url}/api/generate"

        # Preferred engine from config
        preferred = os.environ.get("AI_PREFERRED_ENGINE", "auto").lower()
        if preferred == "claude":
            self._preferred_engine = ENGINE_CLAUDE
        elif preferred == "ollama":
            self._preferred_engine = ENGINE_OLLAMA
        else:
            # auto: Claude if API key present, else Ollama
            self._preferred_engine = ENGINE_CLAUDE if self._anthropic_key else ENGINE_OLLAMA

        # Engine availability cache
        self._claude_available = None
        self._ollama_available = None
        self._last_probe_time = 0
        self._probe_ttl = 60  # seconds

        # Active engine (set after first probe)
        self._active_engine = None

        logger.info(
            f"[AIService] Initialized | preferred={self._preferred_engine} | "
            f"claude_key={'set' if self._anthropic_key else 'not set'}"
        )

    # ─── Claude Client ────────────────────────────────────────

    def _get_claude_client(self):
        """Lazy-init Anthropic client."""
        if self._claude_client is not None:
            return self._claude_client

        if not self._anthropic_key:
            return None

        try:
            import anthropic
            self._claude_client = anthropic.Anthropic(api_key=self._anthropic_key)
            return self._claude_client
        except ImportError:
            logger.warning("[AIService] anthropic SDK not installed")
            return None
        except Exception as e:
            logger.warning(f"[AIService] Failed to create Anthropic client: {e}")
            return None

    # ─── Engine Probing ───────────────────────────────────────

    def _probe_engines(self):
        """Check which engines are available. Cached for _probe_ttl seconds."""
        now = time.time()
        if (now - self._last_probe_time) < self._probe_ttl and self._active_engine is not None:
            return

        # Probe Claude
        self._claude_available = False
        if self._anthropic_key:
            try:
                import anthropic
                self._claude_available = True
                logger.debug("[AIService] Claude API available (key present, SDK installed)")
            except ImportError:
                logger.info("[AIService] Claude API unavailable (SDK not installed)")

        # Probe Ollama
        self._ollama_available = False
        try:
            resp = httpx.get(f"{self._ollama_base_url}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                self._ollama_available = True
                logger.debug("[AIService] Ollama available")
        except Exception:
            logger.debug("[AIService] Ollama not reachable")

        # Determine active engine
        if self._preferred_engine == ENGINE_CLAUDE and self._claude_available:
            self._active_engine = ENGINE_CLAUDE
        elif self._preferred_engine == ENGINE_OLLAMA and self._ollama_available:
            self._active_engine = ENGINE_OLLAMA
        elif self._claude_available:
            self._active_engine = ENGINE_CLAUDE
        elif self._ollama_available:
            self._active_engine = ENGINE_OLLAMA
        else:
            self._active_engine = ENGINE_REGEX

        self._last_probe_time = now
        logger.info(f"[AIService] Active engine: {self._active_engine}")

    # ─── Low-Level Calls ──────────────────────────────────────

    def _call_claude(self, prompt: str, system: str = "", timeout: float = 120.0, max_tokens: int = 4096) -> str | None:
        """Call Claude API via Anthropic SDK. Returns response text or None."""
        client = self._get_claude_client()
        if client is None:
            return None

        try:
            kwargs = {
                "model": self._claude_model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "timeout": timeout,
            }
            if system:
                kwargs["system"] = system

            message = client.messages.create(**kwargs)
            text = message.content[0].text.strip()

            if not text:
                logger.warning("[AIService] Claude returned empty response")
                return None

            return text

        except Exception as e:
            logger.warning(f"[AIService] Claude call failed: {e}")
            self._claude_available = False
            return None

    def _call_ollama(self, prompt: str, system: str = "", timeout: float = 90.0) -> str | None:
        """Call Ollama generate API. Returns response text or None."""
        try:
            payload = {
                "model": self._ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 4096},
            }
            if system:
                payload["system"] = system

            response = httpx.post(self._ollama_generate_url, json=payload, timeout=timeout)
            response.raise_for_status()

            raw = response.json().get("response", "")
            if not raw.strip():
                logger.warning("[AIService] Ollama returned empty response")
                return None

            return raw

        except httpx.ConnectError:
            logger.info("[AIService] Ollama not reachable")
            self._ollama_available = False
            return None
        except httpx.TimeoutException:
            logger.warning(f"[AIService] Ollama timeout after {timeout}s")
            return None
        except Exception as e:
            logger.warning(f"[AIService] Ollama call failed: {e}")
            self._ollama_available = False
            return None

    # ─── Main Call with Failover ──────────────────────────────

    def call(self, prompt: str, system: str = "", timeout: float = 90.0, max_tokens: int = 4096) -> str | None:
        """
        Call AI with automatic failover: preferred engine -> fallback engine -> None.
        Returns response text or None (caller should then use regex fallback).
        """
        self._probe_engines()

        # Build ordered engine list: preferred first, then fallback
        engines = []
        if self._active_engine == ENGINE_CLAUDE:
            engines = [ENGINE_CLAUDE, ENGINE_OLLAMA]
        elif self._active_engine == ENGINE_OLLAMA:
            engines = [ENGINE_OLLAMA, ENGINE_CLAUDE]
        else:
            # Both unavailable, try both anyway in case of transient failure
            engines = [ENGINE_CLAUDE, ENGINE_OLLAMA]

        for engine in engines:
            if engine == ENGINE_CLAUDE and self._anthropic_key:
                result = self._call_claude(prompt, system, timeout, max_tokens)
                if result:
                    if self._active_engine != ENGINE_CLAUDE:
                        logger.info("[AIService] Failover to Claude succeeded")
                        self._active_engine = ENGINE_CLAUDE
                    return result

            elif engine == ENGINE_OLLAMA:
                result = self._call_ollama(prompt, system, timeout)
                if result:
                    if self._active_engine != ENGINE_OLLAMA:
                        logger.info("[AIService] Failover to Ollama succeeded")
                        self._active_engine = ENGINE_OLLAMA
                    return result

        # Both failed
        logger.warning("[AIService] All AI engines failed, returning None (regex fallback)")
        self._active_engine = ENGINE_REGEX
        return None

    # ─── Status ───────────────────────────────────────────────

    def get_status(self) -> dict:
        """
        Get current AI engine status for health endpoint.
        Returns: {"engine": "claude"|"ollama"|"regex", "available": bool, "model": str}
        """
        self._probe_engines()

        if self._active_engine == ENGINE_CLAUDE:
            return {
                "engine": ENGINE_CLAUDE,
                "available": True,
                "model": self._claude_model,
            }
        elif self._active_engine == ENGINE_OLLAMA:
            return {
                "engine": ENGINE_OLLAMA,
                "available": True,
                "model": self._ollama_model,
            }
        else:
            return {
                "engine": ENGINE_REGEX,
                "available": True,  # regex always works
                "model": "regex-fallback",
            }

    def invalidate_cache(self):
        """Force re-probe on next call."""
        self._last_probe_time = 0
        self._active_engine = None


# ─── Singleton ────────────────────────────────────────────────

_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    """Get or create the singleton AIService instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
