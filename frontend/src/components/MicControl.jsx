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
        <div className="segmented">
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
            title={vadReady ? "" : "Manos libres no disponible"}
          >
            Manos libres
          </button>
        </div>
        <button
          className="interrupt"
          onClick={() => send({ type: "interrupt" })}
          title="Interrumpir la voz actual"
        >
          ⏹
        </button>
      </div>

      <div className="input-row">
        {mode === "push_to_talk" ? (
          <button
            className={`mic ${holding ? "rec" : ""}`}
            onMouseDown={startPtt}
            onMouseUp={stopPtt}
            onMouseLeave={stopPtt}
            onTouchStart={(e) => {
              e.preventDefault();
              startPtt();
            }}
            onTouchEnd={(e) => {
              e.preventDefault();
              stopPtt();
            }}
            disabled={!voiceReady}
            title={voiceReady ? "Mantén pulsado para hablar" : "Voz no disponible"}
          >
            {holding && <span className="mic-ripple" />}
            <span className="mic-glyph">🎙️</span>
          </button>
        ) : (
          <div className={`hands-free ${processing ? "busy" : "listening"}`}>
            <span className="hf-wave" aria-hidden>
              <i /><i /><i /><i /><i />
            </span>
            {processing ? "Procesando…" : "Escuchando — habla cuando quieras"}
          </div>
        )}

        <form className="text-input" onSubmit={submit}>
          <input
            type="text"
            placeholder={
              mode === "push_to_talk"
                ? "Mantén el micro o escribe aquí…"
                : "…o escribe tu mensaje"
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button type="submit" disabled={!text.trim()}>
            ➤
          </button>
        </form>
      </div>

      {mode === "push_to_talk" && (
        <div className="mic-hint">
          {holding ? "Grabando… suelta para enviar" : "Mantén pulsado el micrófono para hablar"}
        </div>
      )}
    </div>
  );
}
