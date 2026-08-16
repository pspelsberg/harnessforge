import {apiJson} from "../../shared/api";
import type {ForgeNode, ForgeEdge} from "./graphStore";

export type GeneratedGraphResponse = {
  schema_version: "1";
  id: string;
  name: string;
  workspace_path: string;
  nodes: ForgeNode[];
  edges: ForgeEdge[];
  settings?: {
    review_only: boolean;
    external_dataflow_activated: boolean;
  };
};

export async function generateGraphWithLlm(
  prompt: string,
  model: string = "qwen2.5-coder:32b",
  token: string = ""
): Promise<GeneratedGraphResponse> {
  if (!prompt.trim()) {
    throw new Error("Bitte gib eine Beschreibung für den Agenten-Graph ein.");
  }
  return apiJson<GeneratedGraphResponse>("/api/graph/generate", {
    method: "POST",
    body: JSON.stringify({
      prompt: prompt.trim(),
      model: model.trim() || "qwen2.5-coder:32b",
    }),
    token,
  });
}
