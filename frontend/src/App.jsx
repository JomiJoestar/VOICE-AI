import { useCallback, useEffect, useRef, useState } from "react";
import { useSocket } from "./ws/useSocket.js";
import ChatTimeline from "./components/ChatTimeline.jsx";
import AgentPanel from "./components/AgentPanel.jsx";
import MicControl from "./components/MicControl.jsx";

const AGENTS = ["orquestador", "especialista"];

export default function App() {
  const [status, setStatus] = useState({ volumes: {}, input_mode: "push_to_talk" });
  const [messages, setMessages] = useState([]);
  const [live, setLive] = useState({}); // speaker -> texto en curso
  const [speaking, setSpeaking] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const liveRef = useRef({});
  const speakOffTimer = useRef(null);

  // Suaviza el parpadeo del indicador: no apaga "hablando" al instante.
  const setSpeakingSmooth = useCallback((speaker, active) => {
    if (active) {
      clearTimeout(speakOffTimer.current);
      setSpeaking(speaker);
    } else {
      clearTimeout(speakOffTimer.current);
      speakOffTimer.current = setTimeout(() => {
        setSpeaking((cur) => (cur === speaker ? null : cur));
      }, 450);
    }
  }, []);

  const onEvent = useCallback(
    (ev) => {
      switch (ev.type) {
        case "status":
          setStatus(ev);
          break;
        case "history":
          setMessages(ev.messages || []);
          break;
        case "agent_message": {
          const { type, ...msg } = ev;
          setMessages((m) => [...m, msg]);
          liveRef.current = { ...liveRef.current, [ev.speaker]: "" };
          setLive({ ...liveRef.current });
          break;
        }
        case "token": {
          const prev = liveRef.current[ev.speaker] || "";
          liveRef.current = { ...liveRef.current, [ev.speaker]: prev + ev.text };
          setLive({ ...liveRef.current });
          break;
        }
        case "speaking":
          setSpeakingSmooth(ev.speaker, ev.active);
          break;
        case "state":
          if ("processing" in ev) setProcessing(ev.processing);
          break;
        case "error":
          setError(ev.message);
          setTimeout(() => setError(null), 6000);
          break;
        default:
          break;
      }
    },
    [setSpeakingSmooth]
  );

  const { connected, send } = useSocket(onEvent);

  const sendText = (text) => send({ type: "text_input", text });
  const setVolume = (agent, value) => {
    setStatus((s) => ({ ...s, volumes: { ...s.volumes, [agent]: value } }));
    send({ type: "set_volume", agent, value });
  };
  const setMode = (mode) => {
    setStatus((s) => ({ ...s, input_mode: mode }));
    send({ type: "set_mode", mode });
  };

  return (
    <div className="app">
      <div className="aurora" aria-hidden />
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">◍</span>
          <div>
            <h1>VOICE&nbsp;AI</h1>
            <p className="brand-sub">agentes conversacionales por voz</p>
          </div>
        </div>
        <div className="badges">
          <Badge ok={connected} label={connected ? "conectado" : "reconectando…"} pulse />
          <Badge ok={status.llm_ready} label="LLM" />
          <Badge ok={status.voice_ready} label="voz" />
          <Badge ok={status.vad_ready} label="manos libres" />
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-title">Agentes</div>
          {AGENTS.map((a) => (
            <AgentPanel
              key={a}
              agent={a}
              volume={status.volumes?.[a] ?? 1}
              speaking={speaking === a}
              onVolume={(v) => setVolume(a, v)}
            />
          ))}
          <div className="hint">
            <span className="hint-icon">{status.audible_inter_agent ? "🔊" : "💬"}</span>
            {status.audible_inter_agent
              ? "Oirás cómo Aura y Tobías se coordinan en voz alta."
              : "Coordinación interna en modo texto."}
          </div>
        </aside>

        <main className="main">
          <ChatTimeline
            messages={messages}
            live={live}
            processing={processing}
            speaking={speaking}
          />
          <MicControl
            send={send}
            mode={status.input_mode}
            setMode={setMode}
            sendText={sendText}
            voiceReady={status.voice_ready}
            vadReady={status.vad_ready}
            processing={processing}
          />
        </main>
      </div>

      {error && (
        <div className="toast error">
          <span>⚠️</span> {error}
        </div>
      )}
    </div>
  );
}

function Badge({ ok, label, pulse }) {
  return (
    <span className={`badge ${ok ? "on" : "off"}`}>
      <span className={`badge-dot ${pulse && ok ? "pulse" : ""}`} />
      {label}
    </span>
  );
}
