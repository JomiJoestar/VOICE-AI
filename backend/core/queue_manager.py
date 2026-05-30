"""Control de concurrencia y rate-limiting para las llamadas a DeepSeek.

Evita saturar la API cuando el orquestador y el especialista trabajan a la vez:
- Semáforo: limita las llamadas simultáneas.
- Token bucket: limita las llamadas por minuto.
- Reintentos con backoff exponencial ante errores transitorios.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger("voice_ai.queue")

T = TypeVar("T")


class TokenBucket:
    """Limitador de tasa simple (tokens que se rellenan en el tiempo)."""

    def __init__(self, rate_per_minute: int) -> None:
        self.capacity = max(1, rate_per_minute)
        self.tokens = float(self.capacity)
        self.refill_per_sec = self.capacity / 60.0
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._updated
                self.tokens = min(
                    self.capacity, self.tokens + elapsed * self.refill_per_sec
                )
                self._updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.refill_per_sec
                await asyncio.sleep(wait)


class QueueManager:
    """Envuelve cualquier corrutina de llamada al LLM con límites + reintentos."""

    def __init__(
        self,
        max_concurrent: int = 2,
        requests_per_minute: int = 50,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ) -> None:
        self._sema = asyncio.Semaphore(max_concurrent)
        self._bucket = TokenBucket(requests_per_minute)
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    async def run(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        """Ejecuta `coro_factory()` respetando límites y reintentando si falla.

        Se recibe una *factory* (no una corrutina) para poder reintentar.
        """
        async with self._sema:
            await self._bucket.acquire()
            attempt = 0
            while True:
                try:
                    return await coro_factory()
                except Exception as exc:  # noqa: BLE001 — reintentamos genéricamente
                    attempt += 1
                    if attempt > self._max_retries:
                        logger.error("LLM falló tras %d intentos: %s", attempt, exc)
                        raise
                    delay = self._backoff_base * (2 ** (attempt - 1))
                    delay += random.uniform(0, 0.3)  # jitter
                    logger.warning(
                        "LLM error (intento %d/%d): %s — reintentando en %.1fs",
                        attempt, self._max_retries, exc, delay,
                    )
                    await asyncio.sleep(delay)
