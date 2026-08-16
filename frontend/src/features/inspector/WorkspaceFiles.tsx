import {useEffect, useState} from "react";
import {apiJson} from "../../shared/api";

export function WorkspaceFiles({token, onSelect}: {token: string; onSelect: (path: string) => void}) {
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<{files: string[]}>("/api/workspace/list", {token})
      .then(x => setFiles(x.files))
      .catch(() => setError("Workspace unavailable"));
  }, [token]);

  return (
    <aside aria-label="workspace files" style={{display: "flex", flexDirection: "column", gap: 6}}>
      <div style={{fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700, margin: "4px 0"}}>
        Workspace Files ({files.length})
      </div>
      {error && <p role="alert" className="alert-banner">{error}</p>}
      {files.length === 0 && !error && (
        <div style={{fontSize: "0.78rem", color: "#64748b", fontStyle: "italic", padding: "8px 0"}}>
          No workspace files found.
        </div>
      )}
      {files.map(file => (
        <button
          key={file}
          className="forge-btn"
          style={{
            textAlign: "left",
            justifyContent: "flex-start",
            padding: "8px 10px",
            fontSize: "0.78rem",
            background: "#151d2a",
            borderColor: "#1e293b",
          }}
          onClick={() => onSelect(file)}
        >
          {file}
        </button>
      ))}
    </aside>
  );
}