import { useState } from "react";

export default function MicControl({
  send,
  mode,
  setMode,
  sendText,
  voiceReady,
  vadReady,
  processing,
}) {
  const [text, setText] = useState("");
  const [holding, setHolding] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    sendText(t);
    setText("");
  };

  const startPtt = () => {
    if (!voiceReady) return;
    setHolding(true);
    send({ type: "ptt_start" });
  };
  const stopPtt = () => {
    if (!holding) return;
    setHolding(false);
    send({ type: "ptt_stop" });
  };

  return (
    <div className="controls">
      <div className="mode-row">
        <div className="mode-toggle">
          <button
            className={mode === "push_to_talk" ? "active" : ""}
            onClick={() => setMode("push_to_talk")}
          >
            Pulsar para hablar
          </button>
          <button
            className={mode === "hands_free" ? "active" : ""}
            onClick={() => setMode("hands_free")}
            disabled={!vadReady}
            title={vadReady ? "" : "VAD no disponible"}
          >
            Manos libres
          </button>
        </div>
        <button
          className="interrupt"
          onClick={() => send({ type: "interrupt" })}
          title="Interrumpir voz actual"
        >
          ⏹ Interrumpir
        </button>
      </div>

      {mode === "push_to_talk" ? (
        <button
          className={`ptt ${holding ? "rec" : ""}`}
          onMouseDown={startPtt}
          onMouseUp={stopPtt}
          onMouseLeave={stopPtt}
          onTouchStart={startPtt}
          onTouchEnd={stopPtt}
          disabled={!voiceReady}
        >
          {!voiceReady
            ? "Voz no disponible"
            : holding
            ? "🎙️ Grabando… suelta para enviar"
            : "🎙️ Mantén pulsado para hablar"}
        </button>
      ) : (
        <div className={`hands-free-status ${processing ? "busy" : "listening"}`}>
          {processing ? "Procesando…" : "Escuchando… habla cuando quieras"}
        </div>
      )}

      <form className="text-input" onSubmit={submit}>
        <input
          type="text"
          placeholder="…o escribe tu mensaje"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit">Enviar</button>
      </form>
    </div>
  );
}
