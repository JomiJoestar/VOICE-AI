"""Ensamblaje y ciclo de vida de VOICE AI.

Construye y conecta todos los componentes (LLM, agentes, voz, colas, bus) y
expone una fachada sencilla para el servidor web.
"""
from __future__ import annotations

import asyncio
import logging

from .agents.agent import Agent
from .agents.orchestrator import ConversationEngine
from .agents.personas import ESPECIALISTA_PROMPT, ORQUESTADOR_PROMPT
from .config import config
from .core.context_manager import ContextManager
from .core.events import Speaker, ev_speaking
from .core.llm_client import LLMClient
from .core.message_bus import EventBus
from .core.queue_manager import QueueManager
from .core.turn_sequencer import TurnSequencer
from .storage.db import Storage
from .voice.audio_io import AudioPlayer, audio_available
from .voice.factory import create_voice_backend
from .voice.stt import Transcriber
from .voice.tts import SpeechPlayer
from .voice.vad import VoiceActivityDetector

logger = logging.getLogger("voice_ai.app")


class VoiceAIApp:
    def __init__(self) -> None:
        self.bus = EventBus()
        self.storage = Storage()
        self.queue = QueueManager(
            max_concurrent=config.get("queue.max_concurrent_requests", 2),
            requests_per_minute=config.get("queue.requests_per_minute", 50),
            max_retries=config.get("queue.max_retries", 3),
            backoff_base=config.get("queue.backoff_base_seconds", 1.0),
        )
        self.voice_backend = create_voice_backend()
        self.player = AudioPlayer()
        self.speech: SpeechPlayer | None = None
        self.sequencer: TurnSequencer | None = None
        self.vad = VoiceActivityDetector(config.get("input.sample_rate", 16000))
        self.transcriber: Transcriber | None = None
        self.engine: ConversationEngine | None = None

        self.input_mode = config.get("input.mode", "push_to_talk")
        self.voice_ready = False
        self.vad_ready = False
        self.llm_ready = False

    async def startup(self) -> None:
        await self.storage.init()
        self.bus.set_persist(self.storage.persist_event)

        # --- voz (tolerante a fallos: si no hay deps/modelos, sigue en texto) -
        self.speech = SpeechPlayer(self.voice_backend, self.player)
        self.sequencer = TurnSequencer(self.speech.speak, self._on_speaking)
        self.sequencer.start()
        if audio_available():
            try:
                await self.voice_backend.load()
                self.voice_ready = True
                logger.info("Backend de voz '%s' cargado", self.voice_backend.name)
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo cargar el backend de voz (modo texto)")
            try:
                await asyncio.get_running_loop().run_in_executor(None, self.vad.load)
                self.vad_ready = True
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo cargar el VAD (manos libres deshabilitado)")
        else:
            logger.warning("Sin dispositivo de audio: la app funciona en modo texto")

        self.transcriber = Transcriber(self.voice_backend, self.vad)

        # --- LLM + agentes (requiere API key) --------------------------------
        if config.has_api_key:
            llm = LLMClient(self.queue)
            ctx_orq = ContextManager(
                llm,
                max_tokens=config.get("context.max_tokens", 3000),
                keep_last_turns=config.get("context.keep_last_turns", 8),
            )
            ctx_esp = ContextManager(
                llm,
                max_tokens=config.get("context.max_tokens", 3000),
                keep_last_turns=config.get("context.keep_last_turns", 8),
            )
            orquestador = Agent(Speaker.ORQUESTADOR, ORQUESTADOR_PROMPT, ctx_orq)
            especialista = Agent(Speaker.ESPECIALISTA, ESPECIALISTA_PROMPT, ctx_esp)
            self.engine = ConversationEngine(
                orquestador, especialista, llm, self.sequencer, self.bus
            )
            self.llm_ready = True
            logger.info("LLM y agentes listos")
        else:
            logger.warning("Falta DEEPSEEK_API_KEY: la conversación está deshabilitada")

    async def shutdown(self) -> None:
        if self.transcriber:
            await self.transcriber.stop_hands_free()
        if self.sequencer:
            await self.sequencer.stop()

    async def _on_speaking(self, speaker: Speaker, active: bool) -> None:
        await self.bus.publish(ev_speaking(speaker, active))

    def status(self) -> dict:
        return {
            "voice_ready": self.voice_ready,
            "vad_ready": self.vad_ready,
            "llm_ready": self.llm_ready,
            "audio": audio_available(),
            "input_mode": self.input_mode,
            "audible_inter_agent": config.get("audible_inter_agent", True),
            "volumes": self.speech.get_volumes() if self.speech else {},
        }
