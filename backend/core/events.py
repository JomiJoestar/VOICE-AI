"""Tipos de eventos y mensajes compartidos en todo el sistema.

Estos objetos viajan por el bus interno y, serializados, por el WebSocket
hacia el frontend (historial en vivo + indicadores de quién habla).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> float:
    return time.time()


class Speaker(str, Enum):
    USER = "user"
    ORQUESTADOR = "orquestador"
    ESPECIALISTA = "especialista"
    SYSTEM = "system"


class MessageKind(str, Enum):
    USER_INPUT = "user_input"              # lo que dijo el usuario (tras STT)
    SPEECH = "speech"                      # respuesta hablada normal de un agente
    DELEGATION = "delegation"              # orden del líder al especialista (audible)
    DELEGATION_RESULT = "delegation_result"  # respuesta del worker al líder (audible)
    FINAL = "final"                        # síntesis final del líder hacia el usuario
    SYSTEM = "system"                      # avisos del sistema


@dataclass
class AgentMessage:
    """Una intervención de un participante (usuario o agente)."""

    speaker: Speaker
    text: str
    kind: MessageKind = MessageKind.SPEECH
    id: str = field(default_factory=_new_id)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "speaker": self.speaker.value,
            "text": self.text,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
        }


# --- Eventos WebSocket (backend -> frontend) -----------------------------
def ev_transcript(speaker: Speaker, text: str) -> dict[str, Any]:
    return {"type": "transcript", "speaker": speaker.value, "text": text}


def ev_agent_message(msg: AgentMessage) -> dict[str, Any]:
    return {"type": "agent_message", **msg.to_dict()}


def ev_token(speaker: Speaker, text: str, kind: MessageKind = MessageKind.SPEECH) -> dict[str, Any]:
    """Fragmento en vivo para el subtítulo/burbuja en curso (no se persiste)."""
    return {"type": "token", "speaker": speaker.value, "text": text, "kind": kind.value}


def ev_speaking(speaker: Speaker, active: bool) -> dict[str, Any]:
    return {"type": "speaking", "speaker": speaker.value, "active": active}


def ev_state(**kwargs: Any) -> dict[str, Any]:
    return {"type": "state", **kwargs}


def ev_error(message: str) -> dict[str, Any]:
    return {"type": "error", "message": message}
