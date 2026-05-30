"""Cliente DeepSeek (compatible con el SDK de OpenAI).

Expone streaming de tokens y soporte de tool-calling, ambos canalizados a
través del QueueManager para no saturar la API.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from ..config import config
from .queue_manager import QueueManager

logger = logging.getLogger("voice_ai.llm")


@dataclass
class ToolCall:
    """Acumulador de una llamada a herramienta recibida por streaming."""

    id: str = ""
    name: str = ""
    arguments: str = ""

    def parsed_args(self) -> dict[str, Any]:
        try:
            return json.loads(self.arguments or "{}")
        except json.JSONDecodeError:
            logger.warning("Args de tool no parseables: %r", self.arguments)
            return {}


@dataclass
class StreamResult:
    """Resultado acumulado de un stream del LLM."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_call(self) -> bool:
        return any(tc.name for tc in self.tool_calls)


class LLMClient:
    """Acceso a deepseek-chat con control de colas."""

    def __init__(self, queue: QueueManager) -> None:
        self._client = AsyncOpenAI(
            api_key=config.deepseek_api_key,
            base_url=config.deepseek_base_url,
        )
        self._queue = queue
        self._model = config.get("llm.model", "deepseek-chat")
        self._temperature = config.get("llm.temperature", 0.8)
        self._max_tokens = config.get("llm.max_tokens", 512)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Genera eventos del stream.

        Cada evento es uno de:
          {"type": "token", "text": "..."}      -> fragmento de texto
          {"type": "done", "result": StreamResult}

        El control de tasa/concurrencia se aplica al *abrir* el stream.
        """

        async def _open():
            return await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools or None,
                temperature=self._temperature if temperature is None else temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )

        stream = await self._queue.run(_open)

        result = StreamResult()
        tool_map: dict[int, ToolCall] = {}

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if getattr(delta, "content", None):
                result.text += delta.content
                yield {"type": "token", "text": delta.content}

            for tcd in (getattr(delta, "tool_calls", None) or []):
                idx = tcd.index
                tc = tool_map.setdefault(idx, ToolCall())
                if tcd.id:
                    tc.id = tcd.id
                if tcd.function and tcd.function.name:
                    tc.name = tcd.function.name
                if tcd.function and tcd.function.arguments:
                    tc.arguments += tcd.function.arguments

        result.tool_calls = [tool_map[i] for i in sorted(tool_map)]
        yield {"type": "done", "result": result}
