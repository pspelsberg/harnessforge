import { useState } from "react";
import { runRlm, type RlmResult, type RlmSpec } from "./rlmApi";

export function RlmInspector({ token, spec }: { token: string; spec: RlmSpec }) {
  const [maxChildren, setMaxChildren] = useState(1);
  const [enabled, setEnabled] = useState(false);
  const [result, setResult] = useState<RlmResult>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  async function spawn() {
    setBusy(true); setError(undefined);
    try { setResult(await runRlm(spec.run_id, Array.from({ length: Math.min(maxChildren, 8) }, () => spec), spec.context.bindings, token, enabled)); }
    catch { setError("Sub-Agenten konnten nicht gestartet werden"); }
    finally { setBusy(false); }
  }
  return <section aria-label="RLM Inspector">
    <h2>RLM · Context Firewall</h2>
    <p>Maximale Tiefe: {spec.depth}/3 · Kontext: {spec.context.source}</p>
    <label>Child-Agenten <input aria-label="max children" type="number" min={1} max={8} value={maxChildren} onChange={(event) => setMaxChildren(Math.max(1, Math.min(8, Number(event.target.value) || 1)))} /></label>
    <label><input type="checkbox" aria-label="RLM aktivieren" checked={enabled} onChange={event => setEnabled(event.target.checked)} /> RLM explizit aktivieren</label>
    <button type="button" onClick={spawn} disabled={busy || !enabled}>Sub-Agenten starten</button>
    {error && <p role="alert">{error}</p>}
    {result && <div aria-label="RLM result"><strong>{result.status}</strong>{result.children.map((child) => <article key={child.child_run_id}><b>{child.status}</b><p>{child.summary}</p></article>)}</div>}
  </section>;
}
