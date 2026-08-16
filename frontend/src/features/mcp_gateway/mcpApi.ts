import { apiJson } from "../../shared/api";
export type McpServer = { contract_version: "1"; server_id: string; name: string; transport: "stdio" | "http" | "sse"; approved: boolean; approval_fingerprint?: string | null; capabilities: string[] };
export type McpTool = { server_id: string; name: string; description: string; input_schema: Record<string, unknown> };
export function listMcpServers(token: string): Promise<{ servers: McpServer[] }> { return apiJson("/api/mcp/servers", { token }); }
export function approveMcpServer(serverId: string, token: string): Promise<McpServer> { return apiJson(`/api/mcp/servers/${encodeURIComponent(serverId)}/approve`, { method: "POST", token }); }
export function disableMcpServer(serverId: string, token: string): Promise<McpServer> { return apiJson(`/api/mcp/servers/${encodeURIComponent(serverId)}/disable`, { method: "POST", token }); }
