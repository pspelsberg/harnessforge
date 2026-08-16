import {useState} from "react";

export function ActivationDialog({onActivate}: {onActivate: (bindings: string[]) => void}) {
  const [checked, setChecked] = useState(false);
  const [bindings, setBindings] = useState("query");

  const activate = () => {
    if (!checked) return;
    const clean = bindings
      .split(",")
      .map(x => x.trim())
      .filter(Boolean)
      .slice(0, 32);
    onActivate(clean);
  };

  return (
    <section
      aria-label="external dataflow activation"
      style={{
        marginTop: 16,
        padding: "12px 14px",
        background: "rgba(15, 23, 42, 0.7)",
        border: "1px solid rgba(56, 189, 248, 0.3)",
        borderRadius: 8,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{display: "flex", alignItems: "center", gap: 6, color: "#38bdf8", fontWeight: 700, fontSize: "0.82rem"}}>
        <span>🛡️ Externe Cloud-Datenfluss-Freigabe</span>
      </div>

      <p style={{margin: 0, fontSize: "0.75rem", color: "#94a3b8", lineHeight: 1.4}}>
        Beim Aufruf externer Cloud-Provider (z. B. Mistral, Claude, OpenAI) werden aus Datenschutzgründen nur explizit ausgewählte Variablen übermittelt.
      </p>

      <label style={{display: "flex", alignItems: "flex-start", gap: 8, cursor: "pointer", fontSize: "0.76rem", color: "#f8fafc"}}>
        <input
          type="checkbox"
          aria-label="confirm external dataflow"
          checked={checked}
          onChange={e => setChecked(e.target.checked)}
          style={{marginTop: 2, accentColor: "#38bdf8"}}
        />
        <span>Ich bestätige die Übertragung der freigegebenen Variablen an den externen Provider.</span>
      </label>

      <label style={{display: "flex", flexDirection: "column", gap: 4, fontSize: "0.76rem", color: "#94a3b8"}}>
        <span>Freigegebene State-Variablen (kommagetrennt):</span>
        <input
          aria-label="state bindings"
          value={bindings}
          onChange={e => setBindings(e.target.value)}
          placeholder="z.B. query, rag_context"
          className="forge-input"
          style={{
            background: "#090d16",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "6px 10px",
            color: "#f8fafc",
            fontSize: "0.8rem",
          }}
        />
      </label>

      <button
        type="button"
        className="forge-btn forge-btn-primary"
        disabled={!checked}
        onClick={activate}
        style={{
          marginTop: 4,
          padding: "7px 12px",
          fontSize: "0.8rem",
          fontWeight: 600,
          opacity: checked ? 1 : 0.4,
          cursor: checked ? "pointer" : "not-allowed",
          background: checked ? "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)" : "#1e293b",
        }}
      >
        Activate dataflow
      </button>
    </section>
  );
}