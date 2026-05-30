"""Interfaz común de backend de voz (STT + TTS).

╔══════════════════════════════════════════════════════════════════════════╗
║  CONTRATO COMPARTIDO — NO MODIFICAR SIN COORDINAR CON TODO EL EQUIPO        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Cada plataforma implementa esta interfaz en su propio archivo:            ║
║    - backend_apple.py  -> Apple Silicon (MLX + CoreML)      [rama: mac]     ║
║    - backend_cuda.py   -> NVIDIA/AMD (faster-whisper, etc.) [rama: nvidia]  ║
║    - backend_cpu.py    -> fallback portable (lento)        [main]          ║
║                                                                            ║
║  El resto del sistema SOLO conoce esta interfaz. Mientras respetes las     ║
║  firmas y los tipos, tu implementación es intercambiable vía config.yaml.  ║
╚══════════════════════════════════════════════════════════════════════════╝

Convenciones de audio (válidas para TODAS las implementaciones):
  - El audio se maneja como numpy.ndarray float32 mono en el rango [-1.0, 1.0].
  - transcribe() recibe audio a `sample_rate` Hz (típicamente 16000).
  - synthesize() devuelve (samples_float32_mono, sample_rate_del_modelo).
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import numpy as np


class VoiceBackend(ABC):
    """Backend de cómputo de voz. Implementar uno por plataforma."""

    #: identificador legible del backend (p. ej. "apple_silicon", "cuda")
    name: str = "base"

    @abstractmethod
    async def load(self) -> None:
        """Carga y calienta los modelos UNA vez (al arrancar la app).

        Debe dejar STT y TTS listos en memoria para minimizar la latencia del
        primer turno. Operaciones bloqueantes deben ejecutarse en un executor
        (ver `run_blocking`).
        """

    @abstractmethod
    async def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        """Convierte audio (float32 mono) en texto en español.

        Args:
            audio: muestras float32 mono en [-1, 1].
            sample_rate: frecuencia de muestreo del audio entrante (Hz).
        Returns:
            La transcripción en español (puede ser cadena vacía si no hay voz).
        """

    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        """Sintetiza voz a partir de texto.

        Args:
            text: texto en español a hablar.
            voice: identificador/ruta del modelo de voz (ver config.yaml).
        Returns:
            (samples_float32_mono, sample_rate) listos para reproducir.
        """

    async def unload(self) -> None:
        """Libera recursos (opcional)."""
        return None

    # --- utilidad para implementaciones --------------------------------------
    @staticmethod
    async def run_blocking(fn, *args):
        """Ejecuta una función bloqueante (inferencia) sin frenar el event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, fn, *args)
