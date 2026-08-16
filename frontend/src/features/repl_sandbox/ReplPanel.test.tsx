import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReplPanel } from "./ReplPanel";

const mocks = vi.hoisted(() => ({
  create: vi.fn(async () => ({ contract_version: "1" as const, session_id: "repl-1", status: "active" as const, cells: 0 })),
  execute: vi.fn(async () => ({ contract_version: "1" as const, session_id: "repl-1", status: "succeeded" as const, trust_mode: "local_trust" as const, stdout: "<script>alert(1)</script>", result: "<b>text</b>" })),
  interrupt: vi.fn(async () => ({ session_id: "repl-1", status: "closed" as const })),
}));
vi.mock("./replApi", () => ({ createReplSession: mocks.create, executeRepl: mocks.execute, interruptRepl: mocks.interrupt }));

describe("ReplPanel", () => {
  it("keeps Local Trust visible and renders output as text", async () => {
    render(<ReplPanel token="token" />);
    expect(screen.getByText(/Local Trust Mode/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Ausführen" }));
    await waitFor(() => expect(screen.getByText("succeeded")).toBeTruthy());
    expect(screen.queryByRole("script")).toBeNull();
    expect(screen.getByText("<script>alert(1)</script>")).toBeTruthy();
  });
});
