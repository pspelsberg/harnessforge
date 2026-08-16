import { apiJson } from "../../shared/api";

export type ReplSession = { contract_version: "1"; session_id: string; status: "active" | "closed"; cells: number };
export type ReplResult = { contract_version: "1"; session_id: string; status: "succeeded" | "failed" | "limited" | "cancelled"; trust_mode: "local_trust"; stdout: string; result: unknown; error_code?: string | null };

export function createReplSession(token: string): Promise<ReplSession> {
  return apiJson<ReplSession>("/api/repl/sessions", { method: "POST", token });
}
export function executeRepl(sessionId: string, code: string, token: string, inputData: Record<string, unknown> = {}): Promise<ReplResult> {
  return apiJson<ReplResult>(`/api/repl/sessions/${encodeURIComponent(sessionId)}/execute`, { method: "POST", token, body: JSON.stringify({ mode: "local_trust", code, input_data: inputData }) });
}
export function interruptRepl(sessionId: string, token: string): Promise<{ session_id: string; status: "closed" }> {
  return apiJson<{ session_id: string; status: "closed" }>(`/api/repl/sessions/${encodeURIComponent(sessionId)}/interrupt`, { method: "POST", token });
}
