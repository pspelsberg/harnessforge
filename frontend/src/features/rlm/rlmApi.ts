import { apiJson } from "../../shared/api";

export type RlmSpec = { run_id: string; parent_run_id: string; provider: string; prompt: string; context: { contract_version: "1"; source: "trusted" | "untrusted"; origin: string; bindings: string[]; content: unknown }; depth: number; max_tokens: number; external_provider?: boolean; external_dataflow_approved?: boolean };
export type RlmResult = { contract_version: "1"; run_id: string; status: "succeeded" | "failed" | "limited" | "cancelled"; children: Array<{ child_run_id: string; status: string; source: "untrusted"; summary: string }>; summary: string; error_code?: string | null };
export function runRlm(runId: string, specs: RlmSpec[], allowedBindings: string[], token: string, enabled = false): Promise<RlmResult> {
  return apiJson<RlmResult>("/api/rlm/run", { method: "POST", token, body: JSON.stringify({ contract_version: "1", run_id: runId, specs, allowed_bindings: allowedBindings, enabled }) });
}
