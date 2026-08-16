import {it, expect, vi} from "vitest";
import {generateGraphWithLlm} from "./llmBuilderApi";

it("calls /api/graph/generate with prompt and model payload", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({"content-type": "application/json"}),
    json: async () => ({
      schema_version: "1",
      id: "gen-1",
      name: "AI Agent",
      workspace_path: ".",
      nodes: [],
      edges: [],
    }),
  });
  globalThis.fetch = fetchMock;

  const result = await generateGraphWithLlm("Build a testing loop", "qwen2.5-coder:32b", "test-token");
  expect(result.name).toBe("AI Agent");
  expect(fetchMock).toHaveBeenCalled();
});

it("throws an error when prompt is empty", async () => {
  await expect(generateGraphWithLlm("", "qwen2.5-coder:32b", "token")).rejects.toThrow();
});
