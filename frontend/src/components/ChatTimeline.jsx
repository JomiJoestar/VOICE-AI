import { useEffect, useRef } from "react";

const LABELS = {
  user: "Tú",
  orquestador: "Aura · orquestadora",
  especialista: "Tobías · especialista",
  system: "Sistema",
};

const KIND_TAG = {
  delegation: "orden →",
  delegation_result: "respuesta →",
  final: "",
  speech: "",
  user_input: "",
};

export default function ChatTimeline({ messages, live, processing }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, live]);

  const liveBubbles = Object.entries(live || {})
    .filter(([, text]) => text && text.trim())
    .map(([speaker, text]) => ({ id: `live-${speaker}`, speaker, text, live: true }));

  const all = [...messages, ...liveBubbles];

  return (
    <div className="timeline">
      {all.length === 0 && (
        <div className="empty">
          Habla o escribe para empezar. Aura te atenderá y, si hace falta,
          consultará a Tobías en voz alta.
        </div>
      )}
      {all.map((m) => (
        <div key={m.id} className={`bubble ${m.speaker} ${m.live ? "live" : ""}`}>
          <div className="meta">
            <span className="who">{LABELS[m.speaker] || m.speaker}</span>
            {KIND_TAG[m.kind] ? <span className="tag">{KIND_TAG[m.kind]}</span> : null}
          </div>
          <div className="text">{m.text}</div>
        </div>
      ))}
      {processing && <div className="thinking">Pensando…</div>}
      <div ref={endRef} />
    </div>
  );
}
