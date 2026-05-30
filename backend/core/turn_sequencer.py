"""Secuenciador de turnos de voz.

Garantiza que TODO lo que se habla (tú, el orquestador, el especialista) suene
en orden y sin solaparse, aunque el texto se genere en paralelo por streaming.

Funciona como una única cola FIFO con un solo trabajador de reproducción:
los productores encolan frases a medida que el LLM las va generando, y el
trabajador las sintetiza y reproduce una a una. Así se logra el efecto de
"teatro" en el que oyes al líder dar la orden y al especialista responder.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from .events import Speaker

logger = logging.getLogger("voice_ai.turns")

SpeakFn = Callable[[Speaker, str], Awaitable[None]]
SpeakingCb = Callable[[Speaker, bool], Awaitable[None]]


class TurnSequencer:
    def __init__(self, speak_fn: SpeakFn, on_speaking: SpeakingCb) -> None:
        self._queue: asyncio.Queue[tuple[Speaker, str]] = asyncio.Queue()
        self._speak_fn = speak_fn
        self._on_speaking = on_speaking
        self._task: asyncio.Task | None = None
        self._current: Speaker | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._worker())

    async def enqueue(self, speaker: Speaker, text: str) -> None:
        text = text.strip()
        if text:
            await self._queue.put((speaker, text))

    async def join(self) -> None:
        """Espera a que se reproduzca todo lo encolado."""
        await self._queue.join()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _worker(self) -> None:
        while True:
            speaker, text = await self._queue.get()
            try:
                if self._current != speaker:
                    await self._on_speaking(speaker, True)
                    self._current = speaker
                await self._speak_fn(speaker, text)
            except Exception:  # noqa: BLE001
                logger.exception("Error reproduciendo turno de %s", speaker)
            finally:
                self._queue.task_done()
                # Si no quedan frases en cola, marca fin de habla del actual.
                if self._queue.empty() and self._current is not None:
                    await self._on_speaking(self._current, False)
                    self._current = None
