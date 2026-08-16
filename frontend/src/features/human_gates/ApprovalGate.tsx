import { useState } from "react";
import { decideGate, type GateRecord } from "./gatesApi";

export function ApprovalGate({ gate, sessionId, token, onDecision }: { gate: GateRecord; sessionId: string; token: string; onDecision?: (gate: GateRecord) => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  async function decide(decision: "approved" | "denied") {
    setBusy(true); setError(undefined);
    try { onDecision?.(await decideGate(gate.request_id, { request_id: gate.request_id, nonce: gate.nonce, session_id: sessionId, decision }, token)); }
    catch { setError("Freigabe konnte nicht verarbeitet werden"); } finally { setBusy(false); }
  }
  return <dialog open aria-label="Human approval gate"><h2>Freigabe erforderlich</h2><p>Risiko: {gate.preview.risk} · Datenfluss: {gate.preview.dataflow}</p><pre aria-label="Action preview">{gate.preview.command || gate.preview.diff || gate.preview.action}</pre><p>Schreibziele: {gate.preview.write_targets.join(", ") || "keine"}</p>{error && <p role="alert">{error}</p>}<button type="button" disabled={busy || gate.status !== "pending"} onClick={() => void decide("approved")}>Freigeben</button><button type="button" disabled={busy || gate.status !== "pending"} onClick={() => void decide("denied")}>Ablehnen</button></dialog>;
}
