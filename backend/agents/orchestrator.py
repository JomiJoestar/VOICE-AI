"""Motor de orquestación: el líder coordina al especialista.

Aquí vive el flujo completo de un turno del usuario:
  1. El usuario habla -> el Orquestador decide.
  2. Si la tarea lo amerita, DELEGA en el Especialista con una orden hablada
     (que el usuario OYE en tiempo real).
  3. El Especialista responde con su propia voz y contexto.
  4. El Orquestador integra el resultado y da la respuesta final.

Cada frase generada se encola en el TurnSequencer en cuanto se completa, de modo
que el audio empieza a sonar mientras el LLM sigue escribiendo (baja latencia).
"""
from __future__ import annotations

import logging

from ..config import config
from ..core.events import (
    AgentMessage,
    MessageKind,
    Speaker,
    ev_agent_message,
    ev_state,
    ev_token,
    ev_transcript,
)
from ..core.llm_client import LLMClient, StreamResult
from ..core.message_bus import EventBus
from ..core.text_utils import SentenceAccumulator
from ..core.turn_sequencer import TurnSequencer
from .agent import Agent
from .personas import DELEGATE_TOOL
from .specialist import run_specialist

logger = logging.getLogger("voice_ai.orchestrator")


class ConversationEngine:
    def __init__(
        self,
        orquestador: Agent,
        especialista: Agent,
        llm: LLMClient,
        sequencer: TurnSequencer,
        bus: EventBus,
    ) -> None:
        self._orq = orquestador
        self._esp = especialista
        self._llm = llm
        self._seq = sequencer
        self._bus = bus
        self._audible = bool(config.get("audible_inter_agent", True))
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    async def handle_user_input(self, text: str) -> None:
        text = text.strip()
        if not text or self._busy:
            return
        self._busy = True
        try:
            await self._bus.publish(ev_state(processing=True, listening=False))
            await self._publish_message(Speaker.USER, text, MessageKind.USER_INPUT)
            self._orq.add_user(text)

            # --- 1) primer turno del orquestador (con opción de delegar) -----
            messages = await self._orq.build_messages()
            result, spoken = await self._stream_turn(
                Speaker.ORQUESTADOR, messages, MessageKind.SPEECH, tools=[DELEGATE_TOOL]
            )

            if not result.has_tool_call:
                # Respuesta directa: ya se habló por streaming.
                if spoken.strip():
                    self._orq.add_assistant(spoken.strip())
                    await self._publish_message(
                        Speaker.ORQUESTADOR, spoken.strip(), MessageKind.FINAL
                    )
                await self._seq.join()
                return

            # --- 2) delegación al especialista -------------------------------
            await self._run_delegation(result)
            await self._seq.join()
        finally:
            self._busy = False
            await self._bus.publish(ev_state(processing=False, listening=True))

    async def _run_delegation(self, result: StreamResult) -> None:
        tc = next(t for t in result.tool_calls if t.name)
        args = tc.parsed_args()
        instruccion = (args.get("instruccion") or "").strip()
        contexto = (args.get("contexto") or "").strip()

        # Registra la llamada a herramienta en el historial del orquestador.
        self._orq.add_assistant_tool_call(
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": tc.arguments or "{}"},
            }
        )

        # La ORDEN del líder al especialista — el usuario la oye (si audible).
        await self._publish_message(
            Speaker.ORQUESTADOR, instruccion, MessageKind.DELEGATION
        )
        if self._audible and instruccion:
            for sentence in _split(instruccion):
                await self._seq.enqueue(Speaker.ORQUESTADOR, sentence)

        # El ESPECIALISTA responde con su voz y contexto propios.
        async def on_sentence(sentence: str) -> None:
            await self._bus.publish(
                ev_token(Speaker.ESPECIALISTA, sentence + " ", MessageKind.DELEGATION_RESULT)
            )
            if self._audible:
                await self._seq.enqueue(Speaker.ESPECIALISTA, sentence)

        especialista_text = await run_specialist(
            self._esp, self._llm, instruccion, contexto, on_sentence
        )
        await self._publish_message(
            Speaker.ESPECIALISTA, especialista_text, MessageKind.DELEGATION_RESULT
        )

        # El líder recibe el resultado e integra la respuesta final.
        self._orq.add_tool_result(tc.id, especialista_text)
        messages = await self._orq.build_messages()
        _, final_text = await self._stream_turn(
            Speaker.ORQUESTADOR, messages, MessageKind.FINAL, tools=None
        )
        if final_text.strip():
            self._orq.add_assistant(final_text.strip())
            await self._publish_message(
                Speaker.ORQUESTADOR, final_text.strip(), MessageKind.FINAL
            )

    async def _stream_turn(
        self,
        speaker: Speaker,
        messages: list[dict],
        kind: MessageKind,
        tools: list[dict] | None,
    ) -> tuple[StreamResult, str]:
        """Hace streaming de un turno, hablando cada frase en cuanto se cierra."""
        acc = SentenceAccumulator()
        full = ""
        result = StreamResult()
        async for ev in self._llm.stream(messages, tools=tools):
            if ev["type"] == "token":
                full += ev["text"]
                await self._bus.publish(ev_token(speaker, ev["text"], kind))
                for sentence in acc.push(ev["text"]):
                    await self._seq.enqueue(speaker, sentence)
            elif ev["type"] == "done":
                result = ev["result"]
                tail = acc.flush()
                if tail:
                    await self._seq.enqueue(speaker, tail)
        return result, full

    async def _publish_message(
        self, speaker: Speaker, text: str, kind: MessageKind
    ) -> None:
        if not text:
            return
        msg = AgentMessage(speaker=speaker, text=text, kind=kind)
        await self._bus.publish(ev_agent_message(msg))
        if speaker == Speaker.USER:
            await self._bus.publish(ev_transcript(speaker, text))


def _split(text: str) -> list[str]:
    acc = SentenceAccumulator()
    out = acc.push(text)
    tail = acc.flush()
    if tail:
        out.append(tail)
    return out or [text]
