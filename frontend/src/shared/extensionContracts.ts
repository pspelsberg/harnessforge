export const EXTENSION_POLICY = Object.freeze({
  maxRlmDepth: 3,
  maxRlmChildren: 8,
  maxContextBytes: 128 * 1024,
  maxReplCodeBytes: 64 * 1024,
  maxReplOutputBytes: 64 * 1024,
  maxReplSeconds: 30,
  maxMcpSchemaBytes: 128 * 1024,
  maxMcpResponseBytes: 256 * 1024,
  maxMcpCallsPerRun: 32,
  maxForkDepth: 8,
  maxApprovalTtlSeconds: 15 * 60,
  eventsRetentionDays: 30,
  checkpointsRetentionDays: 30,
  suggestionsRetentionDays: 30,
} as const);

export type TrustSource = "trusted" | "untrusted";
export type ContextEnvelope = {
  contract_version: "1";
  source: TrustSource;
  origin: string;
  bindings: string[];
  content: unknown;
};
export type ExtensionEvent = {
  contract_version: "1";
  namespace: string;
  name: string;
  runId: string;
  phase: "started" | "progress" | "succeeded" | "failed" | "cancelled" | "limit_exceeded";
  errorCode?: string;
  payload: Record<string, unknown>;
};

export type ExtensionControl = { contract_version: "1"; command: "cancel" | "interrupt"; requestId: string; reason?: string };

const idPattern = /^[A-Za-z0-9._-]{1,128}$/;
const namePattern = /^[a-z][a-z0-9_.-]{1,63}$/;
const bindingPattern = /^[A-Za-z_][A-Za-z0-9_.-]{0,127}$/;
const secretKeyPattern = /^(authorization|cookie|set_cookie|api[_-]?key|apikey|access_token|refresh_token|token|secret|password)$/i;
const secretValuePattern = /(?:bearer\s+|api[_-]?key\s*[:=])[^\s,;]+/gi;

function assertJsonValue(value: unknown, depth = 0, seen = new WeakSet<object>()): void {
  if (depth > 8) throw new TypeError("JSON value is too deep");
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    if (typeof value === "string" && new TextEncoder().encode(value).byteLength > 128 * 1024) throw new TypeError("string value is too large");
    return;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("number must be finite");
    return;
  }
  if (typeof value !== "object" || seen.has(value)) throw new TypeError("value must be acyclic JSON");
  seen.add(value);
  if (Array.isArray(value)) {
    if (value.length > 128) throw new TypeError("array is too large");
    value.forEach((item) => assertJsonValue(item, depth + 1, seen));
  } else {
    if (Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) throw new TypeError("object must be plain JSON");
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length > 64 || entries.some(([key]) => key.length > 128)) throw new TypeError("object is too large");
    entries.forEach(([, item]) => assertJsonValue(item, depth + 1, seen));
  }
  seen.delete(value);
}

function jsonBytes(value: unknown): number {
  assertJsonValue(value);
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new TypeError("value must be JSON serializable");
  return new TextEncoder().encode(encoded).byteLength;
}

function redactPayload(value: unknown, key: string | undefined, seen: WeakSet<object>): unknown {
  if (key && secretKeyPattern.test(key.replace(/-/g, "_"))) return "[REDACTED]";
  if (typeof value === "string") return value.replace(secretValuePattern, "[REDACTED]").slice(0, 4096);
  if (Array.isArray(value)) {
    if (seen.has(value)) throw new TypeError("cyclic payload");
    seen.add(value);
    const result = value.slice(0, 128).map((item) => redactPayload(item, undefined, seen));
    seen.delete(value);
    return result;
  }
  if (value !== null && typeof value === "object") {
    if (seen.has(value) || (Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null)) throw new TypeError("invalid payload object");
    seen.add(value);
    const result = Object.fromEntries(Object.entries(value as Record<string, unknown>).slice(0, 64).map(([entryKey, item]) => [entryKey, redactPayload(item, entryKey, seen)]));
    seen.delete(value);
    return result;
  }
  return value;
}

export function redactExtensionPayload(value: unknown, key?: string): unknown {
  return redactPayload(value, key, new WeakSet<object>());
}

export function validateContextEnvelope(value: unknown): ContextEnvelope {
  if (value === null || typeof value !== "object") throw new TypeError("invalid context envelope");
  const candidate = value as Partial<ContextEnvelope>;
  if (candidate.source !== "trusted" && candidate.source !== "untrusted") throw new TypeError("invalid context source");
  if (typeof candidate.origin !== "string" || !idPattern.test(candidate.origin)) throw new TypeError("invalid context origin");
  if (!Array.isArray(candidate.bindings) || candidate.bindings.length > 32 || candidate.bindings.some((binding) => typeof binding !== "string" || !bindingPattern.test(binding))) throw new TypeError("invalid context binding");
  if (new Set(candidate.bindings).size !== candidate.bindings.length) throw new TypeError("duplicate context binding");
  const content = candidate.content;
  if (content === undefined || jsonBytes(content) > EXTENSION_POLICY.maxContextBytes) throw new TypeError("context exceeds limit");
  return { contract_version: "1", source: candidate.source, origin: candidate.origin, bindings: [...candidate.bindings], content };
}

export function sanitizeExtensionEvent(value: unknown): ExtensionEvent {
  if (value === null || typeof value !== "object") throw new TypeError("invalid extension event");
  const candidate = value as Partial<ExtensionEvent>;
  const phase = candidate.phase ?? "progress";
  if (typeof candidate.namespace !== "string" || !namePattern.test(candidate.namespace) || typeof candidate.name !== "string" || !namePattern.test(candidate.name) || typeof candidate.runId !== "string" || !idPattern.test(candidate.runId) || !["started", "progress", "succeeded", "failed", "cancelled", "limit_exceeded"].includes(phase) || candidate.payload === null || typeof candidate.payload !== "object" || Array.isArray(candidate.payload)) throw new TypeError("invalid extension event");
  const errorCode = candidate.errorCode;
  const terminal = ["failed", "cancelled", "limit_exceeded"].includes(phase);
  if ((terminal && typeof errorCode !== "string") || (!terminal && errorCode !== undefined)) throw new TypeError("invalid extension event error semantics");
  assertJsonValue(candidate.payload);
  const payload = redactExtensionPayload(candidate.payload) as Record<string, unknown>;
  if (jsonBytes(payload) > EXTENSION_POLICY.maxMcpResponseBytes) throw new TypeError("event exceeds limit");
  return { contract_version: "1", namespace: candidate.namespace, name: candidate.name, runId: candidate.runId, phase, ...(errorCode ? { errorCode } : {}), payload };
}
