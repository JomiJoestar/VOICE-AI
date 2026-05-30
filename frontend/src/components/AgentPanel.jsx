const NAMES = {
  orquestador: { name: "Aura", role: "Orquestadora · líder", initial: "A" },
  especialista: { name: "Tobías", role: "Especialista", initial: "T" },
};

export default function AgentPanel({ agent, volume, speaking, onVolume }) {
  const info = NAMES[agent] || { name: agent, role: "", initial: "?" };
  const muted = volume <= 0.001;

  return (
    <div className={`agent-card ${agent} ${speaking ? "speaking" : ""}`}>
      <div className="agent-head">
        <div className={`avatar ${agent}`}>
          <span className="avatar-initial">{info.initial}</span>
          {speaking && (
            <>
              <span className="ring r1" />
              <span className="ring r2" />
            </>
          )}
        </div>
        <div className="agent-meta">
          <div className="agent-name">{info.name}</div>
          <div className="agent-role">{info.role}</div>
        </div>
        <div className={`equalizer ${speaking ? "on" : ""}`} aria-hidden>
          <span /><span /><span /><span />
        </div>
      </div>

      <div className="vol">
        <button
          className="vol-icon"
          onClick={() => onVolume(muted ? 1 : 0)}
          title={muted ? "Activar voz" : "Silenciar"}
        >
          {muted ? "🔇" : volume > 0.9 ? "🔊" : "🔉"}
        </button>
        <input
          type="range"
          min="0"
          max="1.5"
          step="0.05"
          value={volume}
          onChange={(e) => onVolume(parseFloat(e.target.value))}
          style={{ "--pct": `${(volume / 1.5) * 100}%` }}
        />
        <span className="vol-val">{Math.round(volume * 100)}%</span>
      </div>
    </div>
  );
}
