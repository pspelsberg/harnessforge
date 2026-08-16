import {it, expect, vi} from "vitest";
import {fetchProviderSettings, saveProviderSettings} from "./settingsApi";

it("fetches provider settings from /api/settings/providers", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({"content-type": "application/json"}),
    json: async () => ({
      openai: {configured: true, masked: "sk-1...4a9f"},
      openrouter: {configured: false, masked: null},
      anthropic: {configured: true, masked: "sk-a...test"},
      gemini: {configured: false, masked: null},
      mistral: {configured: true, masked: "mist...1234"},
      ollama: {connected: true, url: "http://127.0.0.1:11434"},
      workspace_env_exists: true,
    }),
  });
  globalThis.fetch = fetchMock;

  const res = await fetchProviderSettings("token-123");
  expect(res.openai.configured).toBe(true);
  expect(res.openai.masked).toBe("sk-1...4a9f");
  expect(res.mistral.configured).toBe(true);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/settings/providers",
    expect.objectContaining({method: "GET"})
  );
});

it("saves provider settings to /api/settings/providers", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({"content-type": "application/json"}),
    json: async () => ({
      openai: {configured: true, masked: "sk-n...1234"},
      openrouter: {configured: false, masked: null},
      anthropic: {configured: false, masked: null},
      gemini: {configured: false, masked: null},
      mistral: {configured: true, masked: "mist...5678"},
      ollama: {connected: true, url: "http://127.0.0.1:11434"},
      workspace_env_exists: true,
    }),
  });
  globalThis.fetch = fetchMock;

  const res = await saveProviderSettings({openai_api_key: "sk-new-key-1234"}, "token-123");
  expect(res.openai.configured).toBe(true);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/settings/providers",
    expect.objectContaining({method: "POST"})
  );
});
