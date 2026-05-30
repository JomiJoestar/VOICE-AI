"""Bus de eventos: difunde el estado de la conversación a los clientes WS.

Es el punto único por el que pasan los mensajes hacia la interfaz (historial en
vivo, indicadores de quién habla, errores). También notifica a un callback de
persistencia para guardar el historial.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger("voice_ai.bus")

Subscriber = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[Subscriber] = set()
        self._persist: Callable[[dict[str, Any]], Awaitable[None]] | None = None
        self._lock = asyncio.Lock()

    def subscribe(self, sub: Subscriber) -> None:
        self._subscribers.add(sub)

    def unsubscribe(self, sub: Subscriber) -> None:
        self._subscribers.discard(sub)

    def set_persist(self, fn: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self._persist = fn

    async def publish(self, event: dict[str, Any]) -> None:
        """Envía un evento a todos los clientes conectados (y lo persiste)."""
        if self._persist is not None:
            try:
                await self._persist(event)
            except Exception:  # noqa: BLE001
                logger.exception("Fallo al persistir evento")

        if not self._subscribers:
            return
        dead: list[Subscriber] = []
        for sub in list(self._subscribers):
            try:
                await sub(event)
            except Exception:  # noqa: BLE001 — cliente caído
                dead.append(sub)
        for sub in dead:
            self.unsubscribe(sub)
