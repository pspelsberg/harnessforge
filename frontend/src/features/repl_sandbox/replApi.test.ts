import { afterEach, describe, expect, it, vi } from "vitest";
import { createReplSession, executeRepl, interruptRepl } from "./replApi";

describe("REPL API", () => {
  afterEach(() => vi.restoreAllMocks());
  it("uses the authenticated bounded session endpoints", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ contract_version: "1", session_id: "repl-1", status: "active", cells: 0 }), { status: 200, headers: { "content-type": "application/json" } }));
    await createReplSession("token");
    await executeRepl("repl/1", "result = 1", "token");
    await interruptRepl("repl/1", "token");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/repl/sessions/repl%2F1/execute");
    const headers = new Headers((fetchMock.mock.calls[1][1] as RequestInit).headers);
    expect(headers.get("x-harnessforge-token")).toBe("token");
  });
});
