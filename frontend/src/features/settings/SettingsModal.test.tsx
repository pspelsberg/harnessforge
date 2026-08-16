import {render, screen, fireEvent, cleanup} from "@testing-library/react";
import {it, expect, vi, afterEach} from "vitest";
import {SettingsModal} from "./SettingsModal";

afterEach(() => {
  cleanup();
});

it("renders SettingsModal when open", () => {
  const onClose = vi.fn();
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({"content-type": "application/json"}),
    json: async () => ({
      openai: {configured: false, masked: null},
      openrouter: {configured: false, masked: null},
      anthropic: {configured: false, masked: null},
      gemini: {configured: false, masked: null},
      mistral: {configured: false, masked: null},
      ollama: {connected: true, url: "http://127.0.0.1:11434"},
      workspace_env_exists: true,
    }),
  });
  globalThis.fetch = fetchMock;

  render(<SettingsModal isOpen={true} onClose={onClose} />);
  expect(screen.getByText(/Einstellungen & API-Schlüssel/i)).toBeTruthy();
  expect(screen.getByLabelText("anthropic api key")).toBeTruthy();
  expect(screen.getByLabelText("openai api key")).toBeTruthy();
  expect(screen.getByLabelText("mistral api key")).toBeTruthy();
});

it("does not render when closed", () => {
  const onClose = vi.fn();
  const {container} = render(<SettingsModal isOpen={false} onClose={onClose} />);
  expect(container.firstChild).toBeNull();
});

it("allows typing and submitting key updates", () => {
  const onClose = vi.fn();
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({"content-type": "application/json"}),
    json: async () => ({
      openai: {configured: true, masked: "sk-n...1234"},
      openrouter: {configured: false, masked: null},
      anthropic: {configured: false, masked: null},
      gemini: {configured: false, masked: null},
      mistral: {configured: false, masked: null},
      ollama: {connected: true, url: "http://127.0.0.1:11434"},
      workspace_env_exists: true,
    }),
  });
  globalThis.fetch = fetchMock;

  render(<SettingsModal isOpen={true} onClose={onClose} />);
  const input = screen.getByLabelText("openai api key") as HTMLInputElement;
  fireEvent.change(input, {target: {value: "sk-new-key-1234"}});
  expect(input.value).toBe("sk-new-key-1234");
});
