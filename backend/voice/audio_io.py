"""Captura y reproducción de audio nativas con sounddevice.

- AudioRecorder: graba del micrófono. Soporta push-to-talk (start/stop) y un
  flujo continuo de frames para el modo manos libres (VAD).
- AudioPlayer: reproduce muestras float32 aplicando volumen por agente.

Toda la E/S de audio vive en Python (no en el navegador): así evitamos los
problemas de permisos de micrófono de los webviews en macOS.
"""
from __future__ import annotations

import logging
import queue
import threading

import numpy as np

try:
    import sounddevice as sd
except Exception as _exc:  # noqa: BLE001 — entorno sin audio
    sd = None
    _SD_ERR = _exc
else:
    _SD_ERR = None

logger = logging.getLogger("voice_ai.audio")


def audio_available() -> bool:
    return sd is not None


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream = None

    # --- push-to-talk --------------------------------------------------------
    def start(self) -> None:
        if sd is None:
            raise RuntimeError(f"sounddevice no disponible: {_SD_ERR}")
        with self._lock:
            self._frames = []

        def _cb(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                logger.debug("audio status: %s", status)
            with self._lock:
                self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=_cb,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return np.zeros(0, dtype=np.float32)
            data = np.concatenate(self._frames, axis=0)
        return data.reshape(-1).astype(np.float32)

    # --- manos libres (flujo de frames) --------------------------------------
    def open_stream(self, blocksize: int = 512) -> "queue.Queue[np.ndarray]":
        """Abre un stream continuo y devuelve una cola de frames mono float32."""
        if sd is None:
            raise RuntimeError(f"sounddevice no disponible: {_SD_ERR}")
        frame_q: "queue.Queue[np.ndarray]" = queue.Queue()

        def _cb(indata, frames, time_info, status):  # noqa: ANN001
            frame_q.put(indata.reshape(-1).astype(np.float32).copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=blocksize,
            callback=_cb,
        )
        self._stream.start()
        return frame_q

    def close_stream(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class AudioPlayer:
    def play(self, samples: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
        """Reproduce (bloqueante). Llamar dentro de un executor."""
        if sd is None:
            logger.warning("Sin salida de audio: %s", _SD_ERR)
            return
        if samples.size == 0:
            return
        data = np.clip(samples * float(volume), -1.0, 1.0).astype(np.float32)
        sd.play(data, samplerate=sample_rate)
        sd.wait()
