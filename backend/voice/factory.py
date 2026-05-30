"""Selección del backend de voz según config.yaml (resuelto en runtime).

Importa de forma diferida (lazy) para que una máquina Apple no necesite tener
instaladas las dependencias de CUDA, ni viceversa.
"""
from __future__ import annotations

import logging

from ..config import config
from .backend import VoiceBackend

logger = logging.getLogger("voice_ai.voice")


def create_voice_backend() -> VoiceBackend:
    choice = (config.get("compute.backend", "cpu") or "cpu").lower()
    logger.info("Backend de voz seleccionado: %s", choice)

    if choice == "apple_silicon":
        from .backend_apple import AppleSiliconBackend
        return AppleSiliconBackend()

    if choice in ("cuda", "rocm"):
        # Implementado por el equipo de GPU en la rama nvidia-amd.
        from .backend_cuda import CudaBackend
        return CudaBackend()

    from .backend_cpu import CpuBackend
    return CpuBackend()
