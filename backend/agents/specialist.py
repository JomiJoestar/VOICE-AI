"""Lógica de invocación del especialista (worker).

El especialista recibe SOLO lo que el orquestador le pasa al delegar (instrucción
+ contexto mínimo), nunca el historial completo del usuario. Así su contexto se
mantiene independiente.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from ..core.events import Speaker
from ..core.llm_client import LLMClient
from ..core.text_utils import SentenceAccumulator
from .agent import Agent

logger = logging.getLogger("voice_ai.specialist")

# Callback: (frase) -> None ; se invoca por cada frase completa para hablarla ya.
SentenceCb = Callable[[str], Awaitable[None]]


async def run_specialist(
    specialist: Agent,
    llm: LLMClient,
    instruccion: str,
    contexto: str,
    on_sentence: SentenceCb,
) -> str:
    """Ejecuta el turno del especialista en streaming.

    Devuelve el texto completo de su respuesta (para que el orquestador lo
    integre como resultado de la herramienta).
    """
    encargo = instruccion if not contexto else f"{instruccion}\n\nContexto: {contexto}"
    specialist.add_user(encargo)

    messages = await specialist.build_messages()
    acc = SentenceAccumulator()
    full = ""

    async for ev in llm.stream(messages):
        if ev["type"] == "token":
            full += ev["text"]
            for sentence in acc.push(ev["text"]):
                await on_sentence(sentence)
        elif ev["type"] == "done":
            tail = acc.flush()
            if tail:
                await on_sentence(tail)

    specialist.add_assistant(full.strip())
    return full.strip()
