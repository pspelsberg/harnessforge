import { useState } from "react";
import { createReplSession, executeRepl, interruptRepl, type ReplResult } from "./replApi";

export function ReplPanel({ token }: { token: string }) {
  const [code, setCode] = useState("result = input_data.get('value')");
  const [enabled, setEnabled] = useState(false);
  const [sessionId, setSessionId] = useState<string>();
  const [result, setResult] = useState<ReplResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  async function run() {
    setBusy(true); setError(undefined);
    try {
      const session = sessionId ? { session_id: sessionId } : await createReplSession(token);
      setSessionId(session.session_id);
      setResult(await executeRepl(session.session_id, code, token));
    } catch { setError("REPL-Ausführung fehlgeschlagen"); } finally { setBusy(false); }
  }
  async function stop() {
    if (!sessionId) return;
    try { await interruptRepl(sessionId, token); setSessionId(undefined); } catch { setError("REPL konnte nicht beendet werden"); }
  }
  return <section aria-label="REPL Sandbox">
    <h2>Python REPL · Local Trust Mode</h2>
    <p>Code läuft begrenzt und nicht als vollständige OS-Sandbox.</p>
    <label><input type="checkbox" aria-label="REPL aktivieren" checked={enabled} onChange={event => setEnabled(event.target.checked)} /> REPL explizit aktivieren</label>
    <textarea aria-label="REPL code" value={code} onChange={(event) => setCode(event.target.value)} maxLength={64 * 1024} />
    <div><button type="button" onClick={run} disabled={busy || !enabled || !code.trim()}>Ausführen</button><button type="button" onClick={stop} disabled={!sessionId || busy}>Unterbrechen</button></div>
    {error && <p role="alert">{error}</p>}
    {result && <output aria-label="REPL result"><strong>{result.status}</strong>{result.stdout && <pre>{result.stdout}</pre>}{result.result !== null && <pre>{JSON.stringify(result.result)}</pre>}</output>}
  </section>;
}
