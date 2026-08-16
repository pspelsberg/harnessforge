import {useEffect, useState} from "react";
import {apiJson} from "../../shared/api";

export type RunStatus = "created" | "validating" | "running" | "succeeded" | "failed" | "cancelled" | "limit_exceeded";
export type RunRecord = {id: string; created_at: string; status?: RunStatus};

export function RunHistory({
  token,
  onSelect,
  onDelete,
}: {
  token: string;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<{runs: RunRecord[]}>("/api/runs", {token})
      .then(x => setRuns(x.runs))
      .catch(() => setError("Run history unavailable"));
  }, [token]);

  return (
    <aside aria-label="run history" style={{display: "flex", flexDirection: "column", gap: 6}}>
      <div style={{fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700, margin: "4px 0"}}>
        Execution Runs ({runs.length})
      </div>
      {error && <p role="alert" className="alert-banner">{error}</p>}
      {runs.length === 0 && !error && (
        <div style={{fontSize: "0.78rem", color: "#64748b", fontStyle: "italic", padding: "8px 0"}}>
          No past runs yet.
        </div>
      )}
      {runs.map(run => (
        <div
          key={run.id}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "8px 10px",
            background: "#151d2a",
            border: "1px solid #1e293b",
            borderRadius: 6,
          }}
        >
          <button
            className="forge-btn"
            style={{
              background: "transparent",
              border: "none",
              padding: 0,
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#38bdf8",
              cursor: "pointer",
            }}
            onClick={() => onSelect(run.id)}
          >
            {run.id}
          </button>
          <strong
            data-status={run.status || "created"}
            style={{
              fontSize: "0.68rem",
              padding: "2px 6px",
              borderRadius: 4,
              background:
                run.status === "succeeded"
                  ? "rgba(16, 185, 129, 0.2)"
                  : run.status === "failed"
                  ? "rgba(239, 68, 68, 0.2)"
                  : "rgba(245, 158, 11, 0.2)",
              color:
                run.status === "succeeded"
                  ? "#34d399"
                  : run.status === "failed"
                  ? "#f87171"
                  : "#fbbf24",
            }}
          >
            {run.status || "created"}
          </strong>
          {onDelete && (
            <button
              aria-label={`delete ${run.id}`}
              className="forge-btn"
              style={{
                padding: "2px 6px",
                fontSize: "0.7rem",
                background: "rgba(239, 68, 68, 0.15)",
                color: "#fca5a5",
                borderColor: "transparent",
              }}
              onClick={() => {
                if (window.confirm("Delete this run permanently?")) onDelete(run.id);
              }}
            >
              Delete
            </button>
          )}
        </div>
      ))}
    </aside>
  );
}
