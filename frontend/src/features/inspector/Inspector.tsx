import {useState} from "react";
import {useGraphStore, type ForgeNode} from "../canvas/graphStore";
import {NodeConfigForm} from "./NodeConfigForm";
import {PromptEditor} from "./PromptEditor";
import {ActivationDialog} from "./ActivationDialog";

export function Inspector({
  node,
  onConfigChange,
  onActivateDataflow,
  onRequestApproval,
}: {
  node?: ForgeNode;
  onConfigChange?: (config: Record<string, unknown>) => void;
  onActivateDataflow?: (bindings: string[]) => void;
  onRequestApproval?: (bindings: string[]) => Promise<string>;
}) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const removeNode = useGraphStore(state => state.removeNode);

  if (!node) {
    return (
      <aside role="region" aria-label="node inspector" className="right-inspector" style={{justifyContent: "center", alignItems: "center", textAlign: "center", color: "#64748b"}}>
        <div style={{fontSize: "2rem", marginBottom: 8}}>🔍</div>
        <p style={{margin: 0, fontWeight: 500}}>Select a node</p>
        <span style={{fontSize: "0.75rem", color: "#475569"}}>Click any node in the canvas to inspect & configure parameters.</span>
      </aside>
    );
  }

  const initial = JSON.stringify(node.data.config, null, 2);
  const value = draft || initial;

  const apply = () => {
    try {
      if (new TextEncoder().encode(value).byteLength > 128 * 1024) {
        setError("Invalid config");
        return;
      }
      setError(null);
      const parsed = JSON.parse(value);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
        setError("Invalid config");
        return;
      }
      const hasForbidden = (val: unknown): boolean => {
        if (Array.isArray(val)) return val.some(hasForbidden);
        if (val && typeof val === "object")
          return Object.entries(val as Record<string, unknown>).some(
            ([key, item]) => /(api[_-]?key|secret|password|token|authorization)/i.test(key) || hasForbidden(item)
          );
        return false;
      };
      if (hasForbidden(parsed)) {
        setError("Invalid config");
        return;
      }
      onConfigChange?.(parsed);
    } catch {
      setError("Invalid config");
    }
  };

  return (
    <aside role="region" aria-label="node inspector" className="right-inspector">
      <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12}}>
        <h2 style={{margin: 0}}>{node.type} Node</h2>
        <div style={{display: "flex", alignItems: "center", gap: 6}}>
          <span style={{fontSize: "0.72rem", background: "#1e293b", padding: "2px 8px", borderRadius: 4, color: "#f59e0b"}}>
            ID: {node.id}
          </span>
          <button
            aria-label={`delete node ${node.id}`}
            title="Knoten löschen"
            style={{
              background: "rgba(239, 68, 68, 0.2)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#fca5a5",
              borderRadius: 4,
              cursor: "pointer",
              padding: "2px 6px",
              fontSize: "0.75rem",
            }}
            onClick={() => removeNode(node.id)}
          >
            🗑️
          </button>
        </div>
      </div>

      {error && <p role="alert" className="alert-banner">{error}</p>}

      {/* Main Parameters */}
      <NodeConfigForm node={node} onChange={onConfigChange || (() => {})} />

      {/* Multi-line Prompt Editor for LLM nodes */}
      {node.type === "llm" && (
        <div style={{marginTop: 12, display: "flex", flexDirection: "column", gap: 10}}>
          <PromptEditor
            value={String(node.data.config.node_prompt || "")}
            onChange={val => onConfigChange?.({...node.data.config, node_prompt: val})}
          />
          <ActivationDialog
            onActivate={bindings => {
              const doApply = (fingerprint?: string) => {
                onConfigChange?.({
                  ...node.data.config,
                  bindings,
                  ...(fingerprint ? {approval_fingerprint: fingerprint} : {}),
                });
                onActivateDataflow?.(bindings);
              };
              if (onRequestApproval) void onRequestApproval(bindings).then(doApply).catch(() => {});
              else doApply();
            }}
          />
        </div>
      )}

      {/* Advanced Raw JSON Editor */}
      <div style={{marginTop: 14, borderTop: "1px solid #1e293b", paddingTop: 14}}>
        <label style={{display: "flex", flexDirection: "column", gap: 4}}>
          <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3}}>
            <span style={{fontWeight: 600, color: "#94a3b8", fontSize: "0.78rem"}}>
              Raw JSON Config
            </span>
            <div
              className="palette-info-btn"
              style={{width: 16, height: 16, fontSize: "0.65rem"}}
              onClick={e => e.preventDefault()}
            >
              ℹ
              <div className="palette-tooltip" style={{width: 230, right: 0, top: "calc(100% + 6px)"}}>
                <strong style={{display: "block", color: "#38bdf8", marginBottom: 3, fontSize: "0.75rem"}}>
                  Raw JSON Config
                </strong>
                Direkte Low-Level JSON-Konfiguration des Nodes. Muss valides JSON sein und darf keine API-Keys oder Secrets enthalten.
              </div>
            </div>
          </div>
          <textarea
            aria-label="node config"
            value={value}
            onChange={e => setDraft(e.target.value)}
          />
        </label>
        <button className="forge-btn forge-btn-primary" style={{width: "100%", marginTop: 4}} onClick={apply}>
          Apply config
        </button>
      </div>

      <button
        className="forge-btn"
        style={{
          width: "100%",
          marginTop: 16,
          background: "rgba(239, 68, 68, 0.15)",
          color: "#fca5a5",
          border: "1px solid rgba(239, 68, 68, 0.3)",
        }}
        onClick={() => removeNode(node.id)}
      >
        🗑️ Knoten löschen
      </button>
    </aside>
  );
}