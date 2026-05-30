"""Reproductor de voz por agente.

`SpeechPlayer.speak` es la función que usa el TurnSequencer para hablar cada
frase: sintetiza con el backend de la plataforma y reproduce aplicando el
volumen del agente (ajustable en vivo desde la UI).
"""
from __future__ import annotations

import logging

from ..config import config
from ..core.events import Speaker
from .audio_io import AudioPlayer
from .backend import VoiceBackend

logger = logging.getLogger("voice_ai.tts")


class SpeechPlayer:
    def __init__(self, backend: VoiceBackend, player: AudioPlayer) -> None:
        self._backend = backend
        self._player = player
        self._voices: dict[str, str] = {}
        self._volumes: dict[str, float] = {}
        for name, cfg in config.get("agents", {}).items():
            self._voices[name] = cfg.get("voice", "")
            self._volumes[name] = float(cfg.get("volume", 1.0))

    def set_volume(self, agent: str, volume: float) -> None:
        self._volumes[agent] = max(0.0, min(1.5, float(volume)))
        logger.info("Volumen de %s -> %.2f", agent, self._volumes[agent])

    def get_volumes(self) -> dict[str, float]:
        return dict(self._volumes)

    async def speak(self, speaker: Speaker, text: str) -> None:
        voice = self._voices.get(speaker.value)
        if not voice:
            logger.debug("Sin voz configurada para %s; no se reproduce", speaker)
            return
        try:
            samples, sr = await self._backend.synthesize(text, voice)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo de síntesis TTS para %s", speaker)
            return
        volume = self._volumes.get(speaker.value, 1.0)
        await VoiceBackend.run_blocking(self._player.play, samples, sr, volume)
