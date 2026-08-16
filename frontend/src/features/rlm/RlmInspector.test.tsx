import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RlmInspector } from "./RlmInspector";

vi.mock("./rlmApi", () => ({ runRlm: vi.fn(async () => ({ contract_version: "1", run_id: "run-1", status: "succeeded", children: [{ child_run_id: "child-1", status: "succeeded", source: "untrusted", summary: "<untrusted> reference" }], summary: "safe" })) }));

describe("RlmInspector", () => {
  it("shows depth/context governance and renders child output as text", async () => {
    render(<RlmInspector token="token" spec={{ run_id: "run-1", parent_run_id: "run-1", provider: "local", prompt: "x", context: { contract_version: "1", source: "untrusted", origin: "rag", bindings: ["query"], content: {} }, depth: 1, max_tokens: 100 }} />);
    expect(screen.getByText(/Context Firewall/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Sub-Agenten starten" }));
    await waitFor(() => expect(screen.getAllByText("succeeded").length).toBeGreaterThan(0));
    expect(screen.getByText("<untrusted> reference")).toBeTruthy();
  });
});
