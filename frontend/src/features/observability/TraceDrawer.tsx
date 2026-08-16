export type TraceEvent = {type: string; payload: Record<string, unknown>};
import {estimateTokens} from "./tokenRadar";

export function TraceDrawer({events, onClear}: {events: TraceEvent[]; onClear?: () => void}) {
  const budget = estimateTokens({history: events.map(e => JSON.stringify(e)).join("\n")});

  return (
    <aside aria-label="trace viewer" style={{display: "flex", flexDirection: "column", height: "100%"}}>
      <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8}}>
        <div style={{display: "flex", alignItems: "center", gap: 12}}>
          <span style={{fontSize: "0.78rem", fontWeight: 700, color: "#f8fafc"}}>Terminal Stream</span>
          <p
            role="status"
            style={{
              margin: 0,
              fontSize: "0.72rem",
              background: budget.over ? "rgba(239, 68, 68, 0.2)" : "#151d2a",
              color: budget.over ? "#fca5a5" : "#38bdf8",
              padding: "2px 8px",
              borderRadius: 4,
              border: "1px solid #1e293b",
            }}
          >
            📊 Tokens {budget.total}/{budget.limit}
            {budget.over ? " (over limit)" : ""}
          </p>
        </div>
        <button
          className="forge-btn"
          style={{padding: "3px 8px", fontSize: "0.72rem"}}
          onClick={onClear}
        >
          Clear trace
        </button>
      </div>

      <div style={{flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4}}>
        {events.length === 0 && (
          <div style={{color: "#475569", fontStyle: "italic", fontSize: "0.75rem", padding: "12px 0"}}>
            No live events yet. Click "Run" on the top toolbar to begin graph execution and observe real-time traces.
          </div>
        )}
        {events.map((event, index) => (
          <pre
            key={index}
            style={{
              margin: 0,
              padding: "4px 8px",
              background: "#0f1623",
              borderRadius: 4,
              borderLeft: `3px solid ${
                event.type.includes("llm")
                  ? "#f59e0b"
                  : event.type.includes("rag")
                  ? "#38bdf8"
                  : event.type.includes("tool")
                  ? "#10b981"
                  : event.type.includes("error") || event.type.includes("failed")
                  ? "#ef4444"
                  : "#64748b"
              }`,
              color: "#e2e8f0",
              fontSize: "0.72rem",
            }}
          >
            <span style={{color: "#94a3b8", marginRight: 8}}>[{event.type}]</span>
            {JSON.stringify(event.payload)}
          </pre>
        ))}
      </div>
    </aside>
  );
}