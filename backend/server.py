"""Servidor FastAPI: WebSocket de tiempo real + servir el frontend."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .app import VoiceAIApp
from .core.events import Speaker, ev_error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_ai.server")

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

app_state = VoiceAIApp()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await app_state.startup()
    yield
    await app_state.shutdown()


api = FastAPI(title="VOICE AI", lifespan=lifespan)


@api.get("/api/status")
async def status():
    return app_state.status()


@api.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    async def sender(event: dict) -> None:
        await ws.send_json(event)

    app_state.bus.subscribe(sender)

    # Estado inicial + historial reciente para reconstruir la UI.
    await ws.send_json({"type": "status", **app_state.status()})
    history = await app_state.storage.recent(limit=100)
    await ws.send_json({"type": "history", "messages": history})

    try:
        while True:
            data = await ws.receive_json()
            await _handle_client_message(data)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Error en WebSocket")
    finally:
        app_state.bus.unsubscribe(sender)


async def _handle_client_message(data: dict) -> None:
    msg_type = data.get("type")

    if msg_type == "text_input":
        text = (data.get("text") or "").strip()
        if not text:
            return
        if not app_state.engine:
            await app_state.bus.publish(ev_error("Falta la API key de DeepSeek."))
            return
        asyncio.create_task(app_state.engine.handle_user_input(text))

    elif msg_type == "ptt_start":
        if app_state.transcriber and app_state.voice_ready:
            app_state.transcriber.start_ptt()

    elif msg_type == "ptt_stop":
        if not (app_state.transcriber and app_state.voice_ready):
            return
        text = await app_state.transcriber.stop_ptt()
        if text and app_state.engine:
            asyncio.create_task(app_state.engine.handle_user_input(text))

    elif msg_type == "set_mode":
        await _set_mode(data.get("mode", "push_to_talk"))

    elif msg_type == "set_volume":
        agent = data.get("agent")
        value = data.get("value")
        if app_state.speech and agent is not None and value is not None:
            app_state.speech.set_volume(agent, float(value))

    elif msg_type == "interrupt":
        # Detiene la cola de habla actual (barge-in).
        if app_state.sequencer:
            await app_state.sequencer.stop()
            app_state.sequencer.start()


async def _set_mode(mode: str) -> None:
    app_state.input_mode = mode
    if not (app_state.transcriber and app_state.voice_ready and app_state.vad_ready):
        return
    if mode == "hands_free":
        async def on_utterance(text: str) -> None:
            if app_state.engine:
                await app_state.engine.handle_user_input(text)

        app_state.transcriber.start_hands_free(on_utterance)
    else:
        await app_state.transcriber.stop_hands_free()


# --- Frontend ------------------------------------------------------------
if FRONTEND_DIST.exists():
    api.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
else:
    @api.get("/", response_class=HTMLResponse)
    async def _no_build() -> str:
        return (
            "<h1>VOICE AI</h1><p>El frontend no está compilado todavía.</p>"
            "<p>Ejecuta: <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code></p>"
        )
