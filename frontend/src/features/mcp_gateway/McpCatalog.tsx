import { useEffect, useState } from "react";
import { approveMcpServer, disableMcpServer, listMcpServers, type McpServer } from "./mcpApi";

export function McpCatalog({ token }: { token: string }) {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [error, setError] = useState<string>();
  async function refresh() { try { setServers((await listMcpServers(token)).servers); } catch { setError("MCP-Katalog konnte nicht geladen werden"); } }
  useEffect(() => { void refresh(); }, []);
  async function toggle(server: McpServer) {
    try { const next = server.approved ? await disableMcpServer(server.server_id, token) : await approveMcpServer(server.server_id, token); setServers((items) => items.map((item) => item.server_id === next.server_id ? next : item)); } catch { setError("MCP-Freigabe konnte nicht geändert werden"); }
  }
  return <section aria-label="MCP Catalog"><h2>MCP Gateway · Review Catalog</h2>{error && <p role="alert">{error}</p>}<ul>{servers.map((server) => <li key={server.server_id}><strong>{server.name}</strong><span>{server.transport}</span><span>{server.approved ? "freigegeben" : "Review erforderlich"}</span><button type="button" onClick={() => void toggle(server)}>{server.approved ? "Deaktivieren" : "Freigeben"}</button></li>)}</ul></section>;
}
