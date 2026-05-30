# VOICE AI

Aplicación de escritorio local de **agentes de IA conversacionales por voz**. Una
agente orquestadora (**Aura**) atiende al usuario y, cuando hace falta, **delega en
voz alta** a un especialista (**Tobías**). Oyes toda la coordinación entre ambas IAs
en tiempo real. Funciona 100% local salvo la llamada al LLM (DeepSeek).

- **LLM:** DeepSeek `deepseek-chat` (formato OpenAI), en streaming.
- **STT/TTS:** locales. Whisper (STT) + Piper (TTS), acelerados por plataforma.
- **Voz por agente:** voz y volumen independientes, ajustables en vivo.
- **Entrada:** *push-to-talk* o *manos libres* (VAD), seleccionable.
- **Baja latencia:** streaming del LLM + síntesis por frases + modelos en caliente.

## Arquitectura

```
 micrófono ─▶ VAD/STT ─▶ ┌──────────────┐  delega (audible)  ┌──────────────┐
                          │ Orquestador  │ ─────────────────▶ │ Especialista │
 altavoz  ◀─ TTS ◀──────  │   (Aura)     │ ◀───── resultado ── │  (Tobías)    │
            ▲             └──────────────┘                    └──────────────┘
            │ TurnSequencer (audio en orden, sin solapes)
            └─ WebSocket ─▶ Frontend React (historial en vivo, volúmenes)
```

- **Contexto independiente por agente:** cada agente tiene su propio historial; lo
  único que cruza es lo que el orquestador pasa al delegar (vía *tool calling*).
- **Cómputo intercambiable:** la interfaz `backend/voice/backend.py` se implementa
  por plataforma y se elige en `config.yaml` (`compute.backend`).

## Estructura

```
backend/   núcleo (agents, core, voice, storage) + server FastAPI
frontend/  React + Vite (UI servida localmente)
config.yaml  configuración (backend de voz, voces, colas, contexto)
main.py    arranca el servidor + ventana pywebview
```

## Modelo de ramas

| Rama         | Responsable        | Contenido propio                         |
|--------------|--------------------|------------------------------------------|
| `main`       | compartido         | núcleo + interfaz `VoiceBackend` + CPU   |
| `mac`        | Apple Silicon      | `backend_apple.py` (MLX + Piper/CoreML)  |
| `nvidia-amd` | NVIDIA/AMD         | `backend_cuda.py` (faster-whisper, etc.) |

Nadie toca el núcleo del otro: solo cambia la implementación detrás de la interfaz.

## Instalación

### 1. Backend (Python 3.11+)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Dependencias de voz según tu plataforma:
pip install -r requirements-mac.txt     # macOS / Apple Silicon
# pip install -r requirements-cuda.txt  # NVIDIA / AMD
```

### 2. Clave de DeepSeek

```bash
cp .env.example .env
# edita .env y pega tu DEEPSEEK_API_KEY
```

### 3. Voces de Piper (español)

Descarga 2 voces `.onnx` (+ su `.json`) en español desde
[rhasspy/piper voices](https://huggingface.co/rhasspy/piper-voices/tree/main/es)
y colócalas en `models/piper/` con los nombres de `config.yaml`
(p. ej. `es_ES-davefx-medium.onnx` y `es_ES-sharvard-medium.onnx`).

> Whisper (modelo MLX en Apple Silicon) se descarga solo en el primer arranque.

### 4. Frontend

```bash
cd frontend && npm install && npm run build
```

## Ejecutar

```bash
python main.py            # ventana de escritorio (pywebview)
python main.py --server   # solo servidor -> abre http://127.0.0.1:8000
```

Para desarrollo del frontend con recarga en caliente: `cd frontend && npm run dev`
(proxy del WebSocket al backend ya configurado en `vite.config.js`).
