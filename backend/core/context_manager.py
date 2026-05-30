"""Gestión del contexto independiente de cada agente.

Cada agente tiene su propio historial. Cuando supera el presupuesto de tokens,
se resume automáticamente la parte antigua y se conservan los últimos turnos.
El resumen lo genera el propio LLM, de forma aislada por agente.
"""
from __future__ import annotations

import logging
from typing import Any

from .llm_client import LLMClient

logger = logging.getLogger("voice_ai.context")


def _approx_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimación barata: ~4 caracteres por token."""
    chars = sum(len(str(m.get("content", "") or "")) for m in messages)
    return chars // 4


class ContextManager:
    """Mantiene el historial de UN agente dentro de su presupuesto."""

    def __init__(
        self,
        llm: LLMClient,
        max_tokens: int = 3000,
        keep_last_turns: int = 8,
    ) -> None:
        self._llm = llm
        self._max_tokens = max_tokens
        self._keep_last_turns = keep_last_turns

    async def maybe_compress(
        self, system_prompt: str, history: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Devuelve un historial (posiblemente resumido) dentro del presupuesto.

        `history` NO incluye el system prompt; se pasa aparte para no resumirlo.
        """
        if _approx_tokens(history) <= self._max_tokens:
            return history

        # Conserva los últimos turnos; resume el resto.
        keep = history[-self._keep_last_turns :]
        to_summarize = history[: -self._keep_last_turns]
        if not to_summarize:
            return history

        logger.info("Comprimiendo contexto (%d mensajes antiguos)", len(to_summarize))
        summary = await self._summarize(to_summarize)
        compressed: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": f"[Resumen de la conversación previa]\n{summary}",
            }
        ]
        compressed.extend(keep)
        return compressed

    async def _summarize(self, messages: list[dict[str, Any]]) -> str:
        transcript = "\n".join(
            f"{m.get('role')}: {m.get('content', '')}" for m in messages
        )
        prompt = [
            {
                "role": "system",
                "content": (
                    "Resume la siguiente conversación en español en pocas frases, "
                    "conservando datos, decisiones y nombres importantes. Sé conciso."
                ),
            },
            {"role": "user", "content": transcript},
        ]
        text = ""
        async for ev in self._llm.stream(prompt, temperature=0.3):
            if ev["type"] == "token":
                text += ev["text"]
        return text.strip()
