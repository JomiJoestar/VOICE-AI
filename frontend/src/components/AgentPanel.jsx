const NAMES = {
  orquestador: { name: "Aura", role: "Orquestadora (líder)" },
  especialista: { name: "Tobías", role: "Especialista" },
};

export default function AgentPanel({ agent, volume, speaking, onVolume }) {
  const info = NAMES[agent] || { name: agent, role: "" };
  return (
    <div className={`agent-card ${agent} ${speaking ? "speaking" : ""}`}>
      <div className="agent-head">
        <span className={`dot ${speaking ? "live" : ""}`} />
        <div>
          <div className="agent-name">{info.name}</div>
          <div className="agent-role">{info.role}</div>
        </div>
      </div>
      <label className="vol">
        <span>Volumen</span>
        <input
          type="range"
          min="0"
          max="1.5"
          step="0.05"
          value={volume}
          onChange={(e) => onVolume(parseFloat(e.target.value))}
        />
        <span className="vol-val">{Math.round(volume * 100)}%</span>
      </label>
    </div>
  );
}
