"""Punto de entrada de VOICE AI.

Arranca el servidor FastAPI (Uvicorn) en un hilo y abre una ventana de escritorio
ligera con pywebview apuntando al servidor local.

Uso:
    python main.py            # ventana de escritorio (pywebview)
    python main.py --server   # solo servidor (abrir en navegador)
"""
from __future__ import annotations

import sys
import threading
import time

import uvicorn

from backend.config import config

HOST = config.get("app.host", "127.0.0.1")
PORT = config.get("app.port", 8000)
URL = f"http://{HOST}:{PORT}"


def _run_server() -> None:
    uvicorn.run("backend.server:api", host=HOST, port=PORT, log_level="info")


def main() -> None:
    server_only = "--server" in sys.argv

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    if server_only:
        print(f"VOICE AI sirviendo en {URL} (Ctrl+C para salir)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nAdiós.")
        return

    # Espera breve a que el servidor levante antes de abrir la ventana.
    time.sleep(1.5)
    import webview  # pywebview

    webview.create_window(
        title=config.get("app.name", "VOICE AI"),
        url=URL,
        width=1100,
        height=760,
        min_size=(820, 600),
    )
    # gui=None deja que pywebview elija el motor nativo (WKWebView en macOS).
    webview.start()


if __name__ == "__main__":
    main()
