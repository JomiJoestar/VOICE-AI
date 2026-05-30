"""Transcripción: orquesta el micrófono, el VAD y el backend de STT.

Soporta los dos modos seleccionables por el usuario:
  - push-to-talk: graba mientras el botón está pulsado (start/stop explícitos).
  - manos libres: escucha continua; el VAD detecta el fin de cada turno.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

import numpy as np

from ..config import config
from .audio_io import AudioRecorder
from .backend import VoiceBackend
from .vad import VoiceActivityDetector

logger = logging.getLogger("voice_ai.stt")

UtteranceCb = Callable[[str], Awaitable[None]]


class Transcriber:
    def __init__(self, backend: VoiceBackend, vad: VoiceActivityDetector) -> None:
        self._backend = backend
        self._vad = vad
        self.sample_rate = config.get("input.sample_rate", 16000)
        self.channels = config.get("input.channels", 1)
        self._recorder = AudioRecorder(self.sample_rate, self.channels)
        self._hands_free_task: asyncio.Task | None = None

    # --- push-to-talk --------------------------------------------------------
    def start_ptt(self) -> None:
        self._recorder.start()

    async def stop_ptt(self) -> str:
        audio = self._recorder.stop()
        if audio.size == 0:
            return ""
        return await self._backend.transcribe(audio, self.sample_rate)

    # --- manos libres --------------------------------------------------------
    def start_hands_free(self, on_utterance: UtteranceCb) -> None:
        if self._hands_free_task is None:
            self._hands_free_task = asyncio.create_task(
                self._hands_free_loop(on_utterance)
            )

    async def stop_hands_free(self) -> None:
        if self._hands_free_task:
            self._hands_free_task.cancel()
            try:
                await self._hands_free_task
            except asyncio.CancelledError:
                pass
            self._hands_free_task = None
        self._recorder.close_stream()

    async def _hands_free_loop(self, on_utterance: UtteranceCb) -> None:
        loop = asyncio.get_running_loop()
        min_silence = config.get("vad.min_silence_ms", 700) / 1000.0
        self._vad.reset()
        frame_q = self._recorder.open_stream(blocksize=512)
        collecting = False
        buffer: list[np.ndarray] = []
        try:
            while True:
                frame = await loop.run_in_executor(None, frame_q.get)
                event = self._vad.process(frame)
                if event == "start":
                    collecting = True
                    buffer = [frame]
                elif collecting:
                    buffer.append(frame)
                    if event == "end":
                        audio = np.concatenate(buffer).astype(np.float32)
                        collecting = False
                        buffer = []
                        text = await self._backend.transcribe(audio, self.sample_rate)
                        if text.strip():
                            await on_utterance(text)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Error en el bucle de manos libres")
        finally:
            self._recorder.close_stream()
            _ = min_silence  # reservado para refinamiento del corte por silencio
