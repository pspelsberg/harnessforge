import {useState} from "react";

export function PromptEditor({value, onChange}: {value: string; onChange: (value: string) => void}) {
  const [draft, setDraft] = useState(value);

  const update = (next: string) => {
    if (new TextEncoder().encode(next).byteLength <= 128 * 1024) {
      setDraft(next);
      onChange(next);
    }
  };

  return (
    <label style={{display: "flex", flexDirection: "column", gap: 4, marginBottom: 12}}>
      <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3}}>
        <span style={{textTransform: "capitalize", fontWeight: 600, color: "#94a3b8", fontSize: "0.78rem"}}>
          Node Prompt
        </span>
        <div
          className="palette-info-btn"
          style={{width: 16, height: 16, fontSize: "0.65rem"}}
          onClick={e => e.preventDefault()}
        >
          ℹ
          <div className="palette-tooltip" style={{width: 230, right: 0, top: "calc(100% + 6px)"}}>
            <strong style={{display: "block", color: "#38bdf8", marginBottom: 3, fontSize: "0.75rem"}}>
              Node Prompt
            </strong>
            Arbeitsauftrag / System-Prompt für diesen LLM-Schritt. Variablen können mit {'{variable_name}'} dynamisch eingebunden werden.
          </div>
        </div>
      </div>
      <textarea
        aria-label="node prompt"
        placeholder="Enter prompt instructions, e.g. Analyze the code: {query}..."
        value={draft}
        onChange={e => update(e.target.value)}
      />
    </label>
  );
}