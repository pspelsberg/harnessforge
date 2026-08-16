import { describe, expect, it } from "vitest";
import { EXTENSION_POLICY, redactExtensionPayload, sanitizeExtensionEvent, validateContextEnvelope } from "./extensionContracts";

describe("extension contracts", () => {
  it("enforces bounded trust-labelled context", () => {
    const envelope = validateContextEnvelope({ source: "untrusted", origin: "rag", bindings: ["query"], content: { text: "reference" } });
    expect(envelope.source).toBe("untrusted");
    expect(() => validateContextEnvelope({ source: "untrusted", origin: "rag", bindings: ["bad path"], content: {} })).toThrow();
    expect(() => validateContextEnvelope({ source: "untrusted", origin: "rag", bindings: ["query"], content: "x".repeat(EXTENSION_POLICY.maxContextBytes) })).toThrow();
  });

  it("redacts secret-shaped extension payloads before display", () => {
    expect(redactExtensionPayload({ api_key: "secret", message: "Bearer abc" })).toEqual({ api_key: "[REDACTED]", message: "[REDACTED]" });
    const event = sanitizeExtensionEvent({ namespace: "repl_sandbox", name: "repl.failed", runId: "run-1", payload: { token: "secret" } });
    expect(event.contract_version).toBe("1");
    expect(event.payload.token).toBe("[REDACTED]");
    expect(() => sanitizeExtensionEvent({ namespace: "repl_sandbox", name: "repl.failed", runId: "run-1", phase: "failed", payload: {} })).toThrow();
  });

  it("rejects non-JSON objects and cyclic payloads", () => {
    expect(() => validateContextEnvelope({ source: "trusted", origin: "repl", bindings: [], content: new Date() })).toThrow();
    const cyclic: Record<string, unknown> = {}; cyclic.self = cyclic;
    expect(() => redactExtensionPayload(cyclic)).toThrow();
  });

  it("rejects malformed extension events and duplicate bindings", () => {
    expect(() => validateContextEnvelope({ source: "untrusted", origin: "rag", bindings: ["query", "query"], content: {} })).toThrow();
    expect(() => sanitizeExtensionEvent({ namespace: "Bad Namespace", name: "event", runId: "run-1", payload: {} })).toThrow();
    expect(() => sanitizeExtensionEvent({ namespace: "repl_sandbox", name: "event", runId: "run-1", payload: { value: undefined } })).toThrow();
  });
});
