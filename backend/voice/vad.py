"""Detección de actividad de voz (silero-vad) para el modo manos libres.

silero es ligero y corre en CPU igual en todas las plataformas, así que vive en
el núcleo compartido (no en los backends por plataforma).
"""
from __future__ import annotations

import logging

import numpy as np

from ..config import config

logger = logging.getLogger("voice_ai.vad")


class VoiceActivityDetector:
    """Envuelve silero-vad para detectar inicio/fin de un turno de habla."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.threshold = config.get("vad.threshold", 0.5)
        self._model = None
        self._vad_iterator = None

    def load(self) -> None:
        import torch  # lazy

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        (_, _, _, vad_iterator_cls, _) = utils
        self._model = model
        self._vad_iterator = vad_iterator_cls(
            model, threshold=self.threshold, sampling_rate=self.sample_rate
        )
        logger.info("silero-vad cargado")

    def reset(self) -> None:
        if self._vad_iterator is not None:
            self._vad_iterator.reset_states()

    def process(self, frame: np.ndarray) -> str | None:
        """Procesa un frame (512 muestras a 16k). Devuelve 'start', 'end' o None."""
        import torch  # lazy

        if self._vad_iterator is None:
            raise RuntimeError("VAD no inicializado (llama a load()).")
        tensor = torch.from_numpy(frame.astype(np.float32))
        result = self._vad_iterator(tensor, return_seconds=False)
        if not result:
            return None
        if "start" in result:
            return "start"
        if "end" in result:
            return "end"
        return None
