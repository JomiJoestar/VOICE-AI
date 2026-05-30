import { useEffect, useRef } from "react";

const META = {
  user: { label: "Tú", initial: "Tú" },
  orquestador: { label: "Aura", initial: "A" },
  especialista: { label: "Tobías", initial: "T" },
  system: { label: "Sistema", initial: "S" },
};

const KIND_TAG = {
  delegation: "📋 orden a Tobías",
  delegation_result: "💡 respuesta de Tobías",
};

export default function ChatTimeline({ messages, live, processing, speaking }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, live, processing]);

  const liveBubbles = Object.entries(live || {})
    .filter(([, text]) => text && text.trim())
    .map(([speaker, text]) => ({ id: `live-${speaker}`, speaker, text, live: true }));

  const all = [...messages, ...liveBubbles];

  return (
    <div className="timeline">
      {all.length === 0 && !processing && (
        <div className="empty">
          <div className="empty-orb">◍</div>
          <h2>Hola, soy Aura</h2>
          <p>
            Háblame o escríbeme. Si la pregunta lo necesita, consultaré a Tobías
            en voz alta y oirás cómo nos coordinamos.
          </p>
          <div className="empty-chips">
            <span>“¿Qué tiempo hace en Bogotá?”</span>
            <span>“Analiza si me conviene SSD o HDD para editar video”</span>
          </div>
        </div>
      )}

      {all.map((m) => {
        const meta = META[m.speaker] || { label: m.speaker, initial: "?" };
        const isUser = m.speaker === "user";
        return (
          <div
            key={m.id}
            className={`row ${m.speaker} ${isUser ? "right" : "left"} ${
              m.live ? "live" : ""
            }`}
          >
            {!isUser && (
              <div className={`bubble-avatar ${m.speaker}`}>{meta.initial}</div>
            )}
            <div className={`bubble ${m.speaker}`}>
              <div className="meta">
                <span className="who">{meta.label}</span>
                {KIND_TAG[m.kind] ? <span className="tag">{KIND_TAG[m.kind]}</span> : null}
                {m.live && speaking === m.speaker ? (
                  <span className="speaking-pill">hablando…</span>
                ) : null}
              </div>
              <div className="text">
                {m.text}
                {m.live ? <span className="caret" /> : null}
              </div>
            </div>
          </div>
        );
      })}

      {processing && (
        <div className="row left">
          <div className="bubble-avatar orquestador">A</div>
          <div className="bubble thinking">
            <span className="dots"><i /><i /><i /></span>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
