import {useState, useEffect} from "react";
import type {ForgeNode} from "../canvas/graphStore";
import {apiJson} from "../../shared/api";
import {getSessionToken} from "../../shared/session";

const POPULAR_MODELS = [
  {id: "qwen2.5-coder:32b", label: "qwen2.5-coder:32b (Recommended Local Code)"},
  {id: "deepseek-r1:32b", label: "deepseek-r1:32b (Reasoning)"},
  {id: "llama3.3:70b", label: "llama3.3:70b (General)"},
  {id: "mistral-small:24b", label: "mistral-small:24b (Local Ollama)"},
  {id: "phi4:14b", label: "phi4:14b"},
  {id: "codestral-latest", label: "codestral-latest (Mistral Coding Specialist)"},
  {id: "mistral-large-latest", label: "mistral-large-latest (Mistral Large 2)"},
  {id: "mistral-medium-latest", label: "mistral-medium-latest (Mistral Medium 3.5)"},
  {id: "mistral-small-latest", label: "mistral-small-latest (Mistral Small 3 / 24B)"},
  {id: "open-mistral-nemo", label: "open-mistral-nemo (Mistral Nemo 12B)"},
  {id: "ministral-8b-latest", label: "ministral-8b-latest (Mistral Edge)"},
  {id: "claude-sonnet-5", label: "claude-sonnet-5 (Anthropic Coding & Agents)"},
  {id: "claude-opus-5", label: "claude-opus-5 (Anthropic Deep Reasoning)"},
  {id: "claude-fable-5", label: "claude-fable-5 (Anthropic Specialized)"},
  {id: "gpt-5.6-luna", label: "gpt-5.6-luna (OpenAI Fast & Agentic)"},
  {id: "gpt-5.6-terra", label: "gpt-5.6-terra (OpenAI Balanced)"},
  {id: "gpt-5.6-sol", label: "gpt-5.6-sol (OpenAI Heavy Compute)"},
  {id: "gemini-3.7-flash", label: "gemini-3.7-flash (Google High Speed)"},
  {id: "gemini-2.5-pro", label: "gemini-2.5-pro (Google Multimodal)"},
];

const FIELD_DESCRIPTIONS: Record<string, string> = {
  model: "Das zu verwendende KI-Modell (lokales Ollama oder Cloud-Provider wie Claude 5, GPT-5.6, Gemini 3).",
  temperature: "Kreativitätsfaktor (0 = deterministisch & präzise für Code, 1-2 = kreativer für Text).",
  "database path": "Verzeichnis der lokalen LanceDB Vektordatenbank oder Dokumentenablage im Workspace.",
  table: "Name der Tabelle in der LanceDB Vektordatenbank (z. B. 'docs' oder 'code').",
  "top-k": "Anzahl der ähnlichsten Text-/Code-Abschnitte (1 bis 20), die in den Kontext geladen werden.",
  "condition type": "Vergleichsmethode für die Schleifen-Bedingung: 'equals', 'regex', 'number' oder 'exists'.",
  "condition key": "Feldname im State, der nach jedem Schritt überprüft wird (z. B. 'exit_code' oder 'status').",
  "condition value": "Erwarteter Wert für die erfolgreiche Weiterleitung auf den 'true'-Pfad.",
  "max iterations": "Maximale Schleifendurchläufe (1 bis 50) zum Schutz vor unendlichen Loops.",
  fallback: "Ziel-Node-ID, zu der gesprungen wird, falls das Schleifenlimit erreicht wird.",
  operation: "State-Aktion (z. B. 'SET' zum Setzen, 'APPEND' zum Anhängen, 'MERGE' zum Zusammenführen).",
  "source path": "Quelldatei oder State-Schlüssel, aus dem die Daten gelesen werden.",
  target: "Ziel-Schlüssel im State, unter dem das Ergebnis gespeichert wird.",
  "script path": "Dateipfad zum lokalen Python-Skript oder CLI-Befehl (z. B. 'pytest' oder 'scripts/tool.py').",
  arguments: "Kommandozeilen-Argumente für das Tool, durch Leerzeichen getrennt.",
  "output cap": "Maximal zulässige Ausgabegröße in Bytes (max. 51200 Bytes) zum Schutz vor Speicherüberlastung.",
};

const RAG_PATH_PRESETS = [".lancedb", "data/lancedb", "docs", "data", "workspace"];
const TOOL_PATH_PRESETS = ["pytest", "python", "scripts/tool.py", "tests", "uv run pytest"];

function FieldHeader({label, info}: {label: string; info?: string}) {
  const desc = info || FIELD_DESCRIPTIONS[label.toLowerCase()];
  return (
    <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3}}>
      <span style={{textTransform: "capitalize", fontWeight: 600, color: "#94a3b8", fontSize: "0.78rem"}}>
        {label}
      </span>
      {desc && (
        <div
          className="palette-info-btn"
          style={{width: 16, height: 16, fontSize: "0.65rem"}}
          onClick={e => e.preventDefault()}
        >
          ℹ
          <div className="palette-tooltip" style={{width: 220, right: 0, top: "calc(100% + 6px)"}}>
            <strong style={{display: "block", color: "#38bdf8", marginBottom: 3, fontSize: "0.75rem"}}>
              {label}
            </strong>
            {desc}
          </div>
        </div>
      )}
    </div>
  );
}

function PathPickerInput({
  label,
  value,
  onChange,
  presets = [],
  placeholder = "Select or type path...",
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  presets?: string[];
  placeholder?: string;
}) {
  const [showExplorer, setShowExplorer] = useState(false);
  const [workspaceFiles, setWorkspaceFiles] = useState<string[]>([]);

  useEffect(() => {
    if (showExplorer && workspaceFiles.length === 0) {
      apiJson<{files: string[]}>("/api/workspace/list", {token: getSessionToken()})
        .then(res => setWorkspaceFiles(res.files || []))
        .catch(() => {});
    }
  }, [showExplorer, workspaceFiles.length]);

  const handleNativeFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const relPath = files[0].webkitRelativePath;
      const folderName = relPath ? relPath.split("/")[0] : files[0].name;
      onChange(folderName);
      setShowExplorer(false);
    }
  };

  return (
    <div style={{marginBottom: 12}}>
      <label style={{display: "flex", flexDirection: "column", gap: 4}}>
        <FieldHeader label={label} />
        <div style={{display: "flex", gap: 6}}>
          <input
            aria-label={label}
            placeholder={placeholder}
            value={value}
            onChange={e => onChange(e.target.value)}
            style={{flex: 1}}
          />
          <button
            type="button"
            className="forge-btn"
            title="Dateien & Ordner durchsuchen"
            style={{padding: "4px 8px", fontSize: "0.78rem", background: showExplorer ? "#1e293b" : "#151d2a"}}
            onClick={() => setShowExplorer(!showExplorer)}
          >
            📁 {showExplorer ? "✕" : "Browse"}
          </button>
        </div>
      </label>

      {showExplorer && (
        <div
          style={{
            marginTop: 6,
            padding: 10,
            background: "#090e17",
            border: "1px solid #334155",
            borderRadius: 6,
            fontSize: "0.75rem",
          }}
        >
          <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8}}>
            <span style={{fontWeight: 700, color: "#f8fafc"}}>📂 Workspace & Presets</span>
            <label
              className="forge-btn"
              style={{
                cursor: "pointer",
                padding: "2px 6px",
                fontSize: "0.7rem",
                background: "rgba(56, 189, 248, 0.15)",
                color: "#38bdf8",
                border: "1px solid rgba(56, 189, 248, 0.3)",
              }}
            >
              💻 Ordner öffnen...
              <input
                type="file"
                // @ts-expect-error webkitdirectory is standard in Chromium/Firefox
                webkitdirectory=""
                directory=""
                style={{display: "none"}}
                onChange={handleNativeFolderSelect}
              />
            </label>
          </div>

          {presets.length > 0 && (
            <div style={{marginBottom: 8}}>
              <div style={{fontSize: "0.68rem", color: "#64748b", textTransform: "uppercase", marginBottom: 4}}>
                Empfohlene Pfade:
              </div>
              <div style={{display: "flex", flexWrap: "wrap", gap: 4}}>
                {presets.map(p => (
                  <button
                    key={p}
                    type="button"
                    className="forge-btn"
                    style={{padding: "2px 6px", fontSize: "0.7rem", background: value === p ? "#1e293b" : "#111827"}}
                    onClick={() => {
                      onChange(p);
                      setShowExplorer(false);
                    }}
                  >
                    📁 {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {workspaceFiles.length > 0 && (
            <div>
              <div style={{fontSize: "0.68rem", color: "#64748b", textTransform: "uppercase", marginBottom: 4}}>
                Dateien im Workspace:
              </div>
              <div style={{maxHeight: 110, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2}}>
                {workspaceFiles.map(f => (
                  <button
                    key={f}
                    type="button"
                    className="forge-btn"
                    style={{
                      textAlign: "left",
                      justifyContent: "flex-start",
                      padding: "3px 6px",
                      fontSize: "0.7rem",
                      background: value === f ? "#1e293b" : "transparent",
                      border: "none",
                    }}
                    onClick={() => {
                      onChange(f);
                      setShowExplorer(false);
                    }}
                  >
                    📄 {f}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function NodeConfigForm({node, onChange}: {node: ForgeNode; onChange: (config: Record<string, unknown>) => void}) {
  const [draft, setDraft] = useState(node.data.config);

  const set = (key: string, value: unknown) => {
    const next = {...draft, [key]: value};
    setDraft(next);
    onChange(next);
  };

  const input = (label: string, value: string, on: (value: string) => void) => (
    <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
      <FieldHeader label={label} />
      <input aria-label={label} value={value} onChange={e => on(e.target.value)} />
    </label>
  );

  return (
    <form aria-label={`${node.type} configuration`}>
      {node.type === "llm" && (
        <>
          <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
            <FieldHeader label="model" />
            <input
              list="model-presets"
              aria-label="model"
              placeholder="Select from dropdown or type..."
              value={String(draft.model || "")}
              onChange={e => set("model", e.target.value)}
            />
            <datalist id="model-presets">
              {POPULAR_MODELS.map(m => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </datalist>
          </label>

          <label style={{display: "flex", flexDirection: "column", gap: 4, marginTop: -4, marginBottom: 12}}>
            <span style={{fontSize: "0.72rem", color: "#64748b"}}>⚡ Quick select preset</span>
            <select
              aria-label="model preset selector"
              value={String(draft.model || "")}
              onChange={e => {
                if (e.target.value) set("model", e.target.value);
              }}
              style={{marginTop: 2}}
            >
              <option value="" disabled>
                -- Choose a model preset --
              </option>
              <optgroup label="Local / Ollama">
                <option value="qwen2.5-coder:32b">qwen2.5-coder:32b (Recommended)</option>
                <option value="deepseek-r1:32b">deepseek-r1:32b (Reasoning)</option>
                <option value="llama3.3:70b">llama3.3:70b</option>
                <option value="mistral-small:24b">mistral-small:24b</option>
                <option value="phi4:14b">phi4:14b</option>
              </optgroup>
              <optgroup label="Mistral AI (Native & Cloud)">
                <option value="mistral-small-latest">mistral-small-latest (Mistral Small 3/4)</option>
                <option value="codestral-latest">codestral-latest (Coding Specialist)</option>
                <option value="mistral-large-latest">mistral-large-latest (Mistral Large 2)</option>
                <option value="mistral-medium-latest">mistral-medium-latest (Mistral Medium 3.5)</option>
                <option value="open-mistral-nemo">open-mistral-nemo (Mistral Nemo)</option>
                <option value="ministral-8b-latest">ministral-8b-latest (Ministral 8B)</option>
              </optgroup>
              <optgroup label="Anthropic (Claude 5)">
                <option value="claude-sonnet-5">claude-sonnet-5 (Coding & Agents)</option>
                <option value="claude-opus-5">claude-opus-5 (Deep Reasoning)</option>
                <option value="claude-fable-5">claude-fable-5</option>
              </optgroup>
              <optgroup label="OpenAI (GPT-5.6)">
                <option value="gpt-5.6-luna">gpt-5.6-luna (Fast & Agentic)</option>
                <option value="gpt-5.6-terra">gpt-5.6-terra (Balanced)</option>
                <option value="gpt-5.6-sol">gpt-5.6-sol (Heavy Compute)</option>
              </optgroup>
              <optgroup label="Google (Gemini)">
                <option value="gemini-3.7-flash">gemini-3.7-flash (High Speed)</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              </optgroup>
            </select>
          </label>

          <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
            <FieldHeader label="temperature" />
            <input
              aria-label="temperature"
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={String(draft.temperature ?? 0)}
              onChange={e => set("temperature", Math.min(2, Math.max(0, Number(e.target.value))))}
            />
          </label>
        </>
      )}

      {node.type === "rag" && (
        <>
          <PathPickerInput
            label="database path"
            value={String(draft.path || "")}
            onChange={v => set("path", v)}
            presets={RAG_PATH_PRESETS}
            placeholder="e.g. .lancedb or docs/"
          />
          <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
            <FieldHeader label="table" />
            <input
              list="rag-table-presets"
              aria-label="table"
              placeholder="z.B. docs oder knowledge"
              value={String(draft.table || "")}
              onChange={e => set("table", e.target.value)}
            />
            <datalist id="rag-table-presets">
              {["docs", "knowledge", "code", "chunks", "articles"].map(t => (
                <option key={t} value={t} />
              ))}
            </datalist>
            <div style={{display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4}}>
              <span style={{fontSize: "0.7rem", color: "#64748b", alignSelf: "center"}}>Vorschläge:</span>
              {["docs", "knowledge", "code"].map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => set("table", t)}
                  style={{
                    background: draft.table === t ? "rgba(56, 189, 248, 0.25)" : "rgba(30, 41, 59, 0.6)",
                    border: `1px solid ${draft.table === t ? "#38bdf8" : "#334155"}`,
                    color: draft.table === t ? "#38bdf8" : "#94a3b8",
                    borderRadius: 4,
                    fontSize: "0.68rem",
                    padding: "2px 6px",
                    cursor: "pointer",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </label>
          <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
            <FieldHeader label="top-k" />
            <input
              aria-label="top-k"
              type="number"
              min="1"
              max="20"
              value={String(draft.top_k ?? 5)}
              onChange={e => set("top_k", Math.min(20, Math.max(1, Number(e.target.value))))}
            />
          </label>
        </>
      )}

      {node.type === "loop" && (
        <>
          {input("condition type", String(draft.condition_type || "exists"), v => set("condition_type", v))}
          {input("condition key", String(draft.key || "iteration"), v => set("key", v))}
          {input("condition value", String(draft.value ?? ""), v => set("value", v))}
          <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
            <FieldHeader label="max iterations" />
            <input
              aria-label="max iterations"
              type="number"
              min="1"
              max="50"
              value={String(draft.max_iterations ?? 5)}
              onChange={e => set("max_iterations", Math.min(50, Math.max(1, Number(e.target.value))))}
            />
          </label>
          {input("fallback", String(draft.fallback || ""), v => set("fallback", v))}
        </>
      )}

      {node.type === "reducer" && (
        <>
          {input("operation", String(draft.op || "SET"), v => set("op", v))}
          <PathPickerInput
            label="source path"
            value={String(draft.source_path || "")}
            onChange={v => set("source_path", v)}
            presets={["state.json", "output.md", "context.txt"]}
            placeholder="e.g. state.json"
          />
          {input("target", String(draft.target || ""), v => set("target", v))}
        </>
      )}

      {node.type === "tool" && (
        <>
          <PathPickerInput
            label="script path"
            value={String(draft.path || "")}
            onChange={v => set("path", v)}
            presets={TOOL_PATH_PRESETS}
            placeholder="e.g. pytest or scripts/run.py"
          />
          {input("arguments", String(draft.args || ""), v => set("args", v.split(" ").slice(0, 32)))}
          <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
            <FieldHeader label="output cap" />
            <input
              aria-label="output cap"
              type="number"
              min="1"
              max="51200"
              value={String(draft.max_output_bytes ?? 51200)}
              onChange={e => set("max_output_bytes", Math.min(51200, Math.max(1, Number(e.target.value))))}
            />
          </label>
          <p style={{fontSize: "0.72rem", color: "#94a3b8", margin: "6px 0"}}>
            🔒 Local Trust Mode: subprocess without OS sandbox.
          </p>
        </>
      )}

      {node.type === "output" && (
        <p style={{fontSize: "0.75rem", color: "#64748b", fontStyle: "italic", margin: "6px 0"}}>
          Final output sink node
        </p>
      )}
    </form>
  );
}