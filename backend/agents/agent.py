"""Clase Agent: contexto INDEPENDIENTE por agente.

Cada agente mantiene su propio historial (lista de mensajes estilo OpenAI). Los
historiales NUNCA se mezclan: lo único que cruza entre agentes es lo que el
orquestador decide pasar explícitamente al delegar.
"""
from __future__ import annotations

from typing import Any

from ..core.context_manager import ContextManager
from ..core.events import Speaker


class Agent:
    def __init__(
        self,
        speaker: Speaker,
        system_prompt: str,
        context_manager: ContextManager,
    ) -> None:
        self.speaker = speaker
        self.system_prompt = system_prompt
        self._ctx = context_manager
        self._history: list[dict[str, Any]] = []

    # --- mutación del historial ---------------------------------------------
    def add_user(self, content: str) -> None:
        self._history.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self._history.append({"role": "assistant", "content": content})

    def add_assistant_tool_call(self, tool_call: dict[str, Any]) -> None:
        """Registra que el asistente invocó una herramienta (para el follow-up)."""
        self._history.append(
            {"role": "assistant", "content": "", "tool_calls": [tool_call]}
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._history.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": content}
        )

    # --- construcción del prompt --------------------------------------------
    async def build_messages(self) -> list[dict[str, Any]]:
        """[system] + historial (resumido si excede el presupuesto)."""
        compressed = await self._ctx.maybe_compress(self.system_prompt, self._history)
        self._history = compressed
        return [{"role": "system", "content": self.system_prompt}, *compressed]

    @property
    def history(self) -> list[dict[str, Any]]:
        return self._history
