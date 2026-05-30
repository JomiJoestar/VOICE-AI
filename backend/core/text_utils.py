"""Utilidades de texto para el pipeline de baja latencia."""
from __future__ import annotations

import re

# Caracteres que cierran una frase hablable.
_BOUNDARY = re.compile(r"[.!?…](?=\s|$)|[\n]")


class SentenceAccumulator:
    """Acumula tokens del LLM y entrega frases completas en cuanto se cierran.

    Permite empezar a sintetizar/hablar la primera frase mientras el modelo
    sigue generando el resto -> latencia percibida mínima.
    """

    def __init__(self, min_chars: int = 12) -> None:
        self._buf = ""
        self._min_chars = min_chars

    def push(self, token: str) -> list[str]:
        self._buf += token
        out: list[str] = []
        while True:
            match = _BOUNDARY.search(self._buf)
            if not match:
                break
            end = match.end()
            sentence = self._buf[:end].strip()
            rest = self._buf[end:]
            # Evita trocear demasiado fino (p. ej. abreviaturas, decimales).
            if len(sentence) < self._min_chars and rest.strip():
                # busca el siguiente límite acumulando más texto
                next_match = _BOUNDARY.search(rest)
                if not next_match:
                    break
            if sentence:
                out.append(sentence)
            self._buf = rest
        return out

    def flush(self) -> str:
        leftover = self._buf.strip()
        self._buf = ""
        return leftover
