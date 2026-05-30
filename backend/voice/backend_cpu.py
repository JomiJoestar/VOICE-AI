"""Backend de voz portable (CPU). Fallback lento pero universal.

Útil para arrancar el proyecto en cualquier máquina. Para producción usa el
backend de tu plataforma (apple_silicon / cuda). Requiere:
    pip install faster-whisper piper-tts onnxruntime
"""
from __future__ import annotations

import logging

import numpy as np

from ..config import config
from .backend import VoiceBackend

logger = logging.getLogger("voice_ai.voice.cpu")


class CpuBackend(VoiceBackend):
    name = "cpu"

    def __init__(self) -> None:
        self._model_size = config.get("stt.model", "small")
        self._language = config.get("stt.language", "es")
        self._whisper = None
        self._voices: dict[str, object] = {}

    async def load(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Falta faster-whisper para el backend CPU. "
                "Instala: pip install faster-whisper piper-tts onnxruntime"
            ) from exc

        self._whisper = WhisperModel(
            self._model_size, device="cpu", compute_type="int8"
        )
        for agent_cfg in config.get("agents", {}).values():
            if agent_cfg.get("voice"):
                self._get_voice(agent_cfg["voice"])
        logger.info("Backend CPU listo (whisper=%s)", self._model_size)

    def _transcribe_sync(self, audio: np.ndarray) -> str:
        segments, _ = self._whisper.transcribe(  # type: ignore[union-attr]
            audio, language=self._language
        )
        return "".join(seg.text for seg in segments).strip()

    async def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        if self._whisper is None:
            raise RuntimeError("Backend CPU no inicializado (llama a load()).")
        audio = np.asarray(audio, dtype=np.float32)
        return await self.run_blocking(self._transcribe_sync, audio)

    def _get_voice(self, voice_path: str):
        if voice_path not in self._voices:
            from piper import PiperVoice  # type: ignore

            self._voices[voice_path] = PiperVoice.load(voice_path)
        return self._voices[voice_path]

    def _synthesize_sync(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        piper_voice = self._get_voice(voice)
        sample_rate = piper_voice.config.sample_rate  # type: ignore[attr-defined]
        chunks = bytearray()
        for raw in piper_voice.synthesize_stream_raw(text):
            chunks.extend(raw)
        pcm = np.frombuffer(bytes(chunks), dtype=np.int16)
        return pcm.astype(np.float32) / 32768.0, sample_rate

    async def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        return await self.run_blocking(self._synthesize_sync, text, voice)
