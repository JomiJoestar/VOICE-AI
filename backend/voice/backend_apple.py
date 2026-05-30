"""Backend de voz para Apple Silicon (MLX + Piper).

STT: mlx-whisper -> usa Metal / Neural Engine (mínima latencia en M-series).
TTS: Piper (onnxruntime) -> síntesis local muy rápida.

Las dependencias se importan de forma diferida para no obligar a otras
plataformas a instalarlas. Instalar con:
    pip install -r requirements.txt -r requirements-mac.txt
"""
from __future__ import annotations

import logging

import numpy as np

from ..config import config
from .backend import VoiceBackend

logger = logging.getLogger("voice_ai.voice.apple")

# Tamaño de modelo Whisper -> repo MLX en Hugging Face.
_MLX_REPOS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
}


class AppleSiliconBackend(VoiceBackend):
    name = "apple_silicon"

    def __init__(self) -> None:
        model_size = config.get("stt.model", "small")
        self._repo = _MLX_REPOS.get(model_size, _MLX_REPOS["small"])
        self._language = config.get("stt.language", "es")
        self._mlx_whisper = None
        self._voices: dict[str, object] = {}  # ruta -> PiperVoice

    async def load(self) -> None:
        # STT: importamos mlx_whisper y calentamos con audio silencioso.
        import mlx_whisper  # type: ignore

        self._mlx_whisper = mlx_whisper
        warm = np.zeros(16000, dtype=np.float32)
        await self.run_blocking(self._transcribe_sync, warm, 16000)
        logger.info("mlx-whisper listo (%s)", self._repo)

        # TTS: pre-cargamos las voces configuradas.
        for agent_cfg in config.get("agents", {}).values():
            voice_path = agent_cfg.get("voice")
            if voice_path:
                self._get_voice(voice_path)
        logger.info("Voces Piper cargadas: %s", list(self._voices))

    # --- STT -----------------------------------------------------------------
    def _transcribe_sync(self, audio: np.ndarray, sample_rate: int) -> str:
        result = self._mlx_whisper.transcribe(  # type: ignore[union-attr]
            audio,
            path_or_hf_repo=self._repo,
            language=self._language,
            fp16=True,
        )
        return (result.get("text") or "").strip()

    async def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        if self._mlx_whisper is None:
            raise RuntimeError("Backend Apple no inicializado (llama a load()).")
        audio = np.asarray(audio, dtype=np.float32)
        return await self.run_blocking(self._transcribe_sync, audio, sample_rate)

    # --- TTS -----------------------------------------------------------------
    def _get_voice(self, voice_path: str):
        if voice_path not in self._voices:
            from piper import PiperVoice  # type: ignore

            self._voices[voice_path] = PiperVoice.load(voice_path)
        return self._voices[voice_path]

    def _synthesize_sync(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        piper_voice = self._get_voice(voice)
        sample_rate = piper_voice.config.sample_rate  # type: ignore[attr-defined]
        parts: list[np.ndarray] = []
        for chunk in piper_voice.synthesize(text):  # un AudioChunk por frase
            parts.append(chunk.audio_float_array)  # float32 mono en [-1, 1]
            sample_rate = chunk.sample_rate
        if not parts:
            return np.zeros(0, dtype=np.float32), sample_rate
        return np.concatenate(parts).astype(np.float32), sample_rate

    async def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        return await self.run_blocking(self._synthesize_sync, text, voice)
