"""
Ollama Client – Production-grade HTTP client for Ollama API with:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Connection pooling
- Comprehensive error handling
"""

import os
import time
import logging
from typing import Optional
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class OllamaClient:
    """Production-grade Ollama HTTP client with resilience patterns."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout_short: float = 30.0,
        timeout_medium: float = 90.0,
        timeout_long: float = 120.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """Initialize Ollama client with resilience parameters."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_short = timeout_short
        self.timeout_medium = timeout_medium
        self.timeout_long = timeout_long
        self.max_retries = max_retries
        
        # Circuit breaker
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failures = 0
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.circuit_last_failure_time = 0
        
        # HTTP client with connection pooling
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_medium,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        
        logger.info(f"OllamaClient initialized | URL: {self.base_url} | Model: {self.model}")
    
    def _check_circuit_breaker(self) -> bool:
        """
        Check circuit breaker state.
        Returns True if circuit is CLOSED (operational), False if OPEN.
        """
        if self.circuit_state == CircuitState.CLOSED:
            return True
        
        if self.circuit_state == CircuitState.OPEN:
            # Check if we should transition to HALF_OPEN
            elapsed = time.time() - self.circuit_last_failure_time
            if elapsed >= self.circuit_breaker_timeout:
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self.circuit_state = CircuitState.HALF_OPEN
                return True
            else:
                logger.warning(f"Circuit breaker OPEN | Recovery in {self.circuit_breaker_timeout - elapsed:.0f}s")
                return False
        
        return True  # HALF_OPEN - allow retry
    
    def _on_success(self):
        """Called on successful request."""
        if self.circuit_state != CircuitState.CLOSED:
            logger.info("Circuit breaker transitioning to CLOSED")
            self.circuit_state = CircuitState.CLOSED
            self.circuit_failures = 0
    
    def _on_failure(self):
        """Called on failed request."""
        self.circuit_failures += 1
        self.circuit_last_failure_time = time.time()
        
        if self.circuit_failures >= self.circuit_breaker_threshold:
            logger.error(f"Circuit breaker OPEN after {self.circuit_failures} failures")
            self.circuit_state = CircuitState.OPEN
    
    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        num_predict: int = 4096,
        timeout: Optional[float] = None,
    ) -> Optional[str]:
        """
        Generate text using Ollama with retry logic.
        
        Args:
            prompt: Input prompt
            system: System message/context
            temperature: Sampling temperature
            num_predict: Max tokens to generate
            timeout: Request timeout (uses medium default if None)
        
        Returns:
            Generated text or None on failure
        """
        if timeout is None:
            timeout = self.timeout_medium
        
        # Check circuit breaker
        if not self._check_circuit_breaker():
            return None
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if system:
            payload["system"] = system
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = self.client.post(
                    "/api/generate",
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                
                result = response.json().get("response", "").strip()
                
                if not result:
                    logger.warning("Ollama returned empty response")
                    self._on_failure()
                    if attempt < self.max_retries - 1:
                        continue
                    return None
                
                self._on_success()
                return result
            
            except httpx.TimeoutException:
                logger.warning(f"Ollama timeout (attempt {attempt + 1}/{self.max_retries})")
                self._on_failure()
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                return None
            
            except httpx.ConnectError as e:
                logger.warning(f"Ollama connection error (attempt {attempt + 1}/{self.max_retries}): {e}")
                self._on_failure()
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                return None
            
            except Exception as e:
                logger.error(f"Ollama error (attempt {attempt + 1}/{self.max_retries}): {e}")
                self._on_failure()
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                return None
        
        return None
    
    def check_status(self) -> dict:
        """
        Check Ollama server status and available models.
        
        Returns:
            {
                "available": bool,
                "models": list[str],
                "model_loaded": bool,
                "circuit_state": str,
            }
        """
        try:
            response = self.client.get("/api/tags", timeout=self.timeout_short)
            response.raise_for_status()
            
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            
            return {
                "available": True,
                "models": models,
                "model_loaded": any(self.model in m for m in models),
                "circuit_state": self.circuit_state.value,
            }
        
        except Exception as e:
            logger.warning(f"Status check failed: {e}")
            return {
                "available": False,
                "models": [],
                "model_loaded": False,
                "circuit_state": self.circuit_state.value,
            }
    
    def close(self):
        """Close HTTP client."""
        try:
            self.client.close()
        except Exception as e:
            logger.warning(f"Error closing client: {e}")


# Global client instance
_client = None


def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client."""
    global _client
    if _client is None:
        _client = OllamaClient(
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            max_retries=int(os.environ.get("OLLAMA_MAX_RETRIES", 3)),
        )
    return _client
