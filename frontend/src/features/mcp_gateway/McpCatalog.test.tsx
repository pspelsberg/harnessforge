import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { McpCatalog } from "./McpCatalog";
vi.mock("./mcpApi", () => ({ listMcpServers: vi.fn(async () => ({ servers: [{ contract_version: "1", server_id: "srv-1", name: "<untrusted>", transport: "stdio", approved: false, capabilities: [] }] })), approveMcpServer: vi.fn(async () => ({ contract_version: "1", server_id: "srv-1", name: "<untrusted>", transport: "stdio", approved: true, capabilities: [] })), disableMcpServer: vi.fn() }));
describe("McpCatalog", () => { it("shows review state and renders server names as text", async () => { render(<McpCatalog token="token" />); await waitFor(() => expect(screen.getByText("<untrusted>")).toBeTruthy()); expect(screen.getByText("Review erforderlich")).toBeTruthy(); }); });
