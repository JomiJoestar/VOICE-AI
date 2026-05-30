"""Backend de voz para NVIDIA (CUDA) / AMD (ROCm).

╔══════════════════════════════════════════════════════════════════════════╗
║  ESTE ARCHIVO LO IMPLEMENTA EL EQUIPO DE GPU EN LA RAMA `nvidia-amd`.       ║
║  Es un ESQUELETO. Rellena los métodos respetando la interfaz VoiceBackend  ║
║  (mismas firmas, mismos tipos). NO modifiques backend.py ni el núcleo.     ║
╚══════════════════════════════════════════════════════════════════════════╝

Plan de implementación sugerido:
  STT: faster-whisper sobre CUDA
       from faster_whisper import WhisperModel
       model = WhisperModel(size, device="cuda", compute_type="float16")
       segments, _ = model.transcribe(audio, language="es")
  TTS: Piper con onnxruntime-gpu (CUDA Execution Provider).
  AMD: usar la build ROCm de onnxruntime y ct2/whisper.cpp con ROCm.

Importa torch/faster_whisper de forma DIFERIDA (lazy), dentro de los métodos,
para que las máquinas Apple no necesiten instalar CUDA.
"""
from __future__ import annotations

import logging

import numpy as np

from ..config import config
from .backend import VoiceBackend

logger = logging.getLogger("voice_ai.voice.cuda")


class CudaBackend(VoiceBackend):
    name = "cuda"

    def __init__(self) -> None:
        self._model_size = config.get("stt.model", "small")
        self._language = config.get("stt.language", "es")
        # TODO(nvidia-amd): inicializar referencias a modelos (lazy).

    async def load(self) -> None:
        # TODO(nvidia-amd): cargar faster-whisper en CUDA y voces Piper (GPU).
        raise NotImplementedError(
            "CudaBackend.load() pendiente — implementar en la rama nvidia-amd."
        )

    async def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        # TODO(nvidia-amd): faster-whisper transcribe -> texto español.
        raise NotImplementedError(
            "CudaBackend.transcribe() pendiente — implementar en la rama nvidia-amd."
        )

    async def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        # TODO(nvidia-amd): Piper (onnxruntime-gpu) -> (float32 mono, sample_rate).
        raise NotImplementedError(
            "CudaBackend.synthesize() pendiente — implementar en la rama nvidia-amd."
        )
