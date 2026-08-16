import { afterEach, describe, expect, it, vi } from "vitest";
import { runRlm, type RlmSpec } from "./rlmApi";

const spec = { run_id: "run-1", parent_run_id: "run-1", provider: "local", prompt: "summarize", context: { contract_version: "1" as const, source: "untrusted" as const, origin: "rag", bindings: ["query"], content: { text: "reference" } }, depth: 1, max_tokens: 100 };
describe("RLM API", () => {
  afterEach(() => vi.restoreAllMocks());
  it("sends bounded context bindings and auth", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ contract_version: "1", run_id: "run-1", status: "succeeded", children: [], summary: "" }), { status: 200 }));
    await runRlm("run-1", [spec as RlmSpec], ["query"], "token");
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(request.body)).allowed_bindings).toEqual(["query"]);
    expect(new Headers(request.headers).get("x-harnessforge-token")).toBe("token");
  });
});
