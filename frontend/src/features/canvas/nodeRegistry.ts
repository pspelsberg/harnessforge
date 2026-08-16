import type {NodeType} from "./graphStore";

export const NODE_LABELS: Record<NodeType, string> = {
  start: "Start",
  llm: "LLM Call",
  rag: "RAG / LanceDB",
  loop: "Loop / Router",
  reducer: "State Reducer",
  tool: "Tool (Local Trust)",
  output: "Output",
};

export const NODE_COLORS: Record<NodeType, string> = {
  start: "#10b981",
  llm: "#f59e0b",
  rag: "#38bdf8",
  loop: "#fb923c",
  reducer: "#fcd34d",
  tool: "#ef4444",
  output: "#10b981",
};

export const NODE_DESCRIPTIONS: Record<NodeType, string> = {
  start: "Startpunkt des Workflows. Nimmt den initialen Benutzer-Prompt oder Input entgegen.",
  llm: "Führt einen LLM-Inferenz-Schritt aus (Ollama lokal oder Cloud) mit Prompt-Templates & Bindings.",
  rag: "Durchsucht die lokale LanceDB Vektordatenbank und reichert den Kontext mit relevanten Chunks an.",
  loop: "Deklarativer Bedingungs-Router für iterative ReAct-Loops und Fehlerkorrekturen.",
  reducer: "Transformiert oder aggregiert Datenfelder im Agent-State (z.B. SET, APPEND, MERGE).",
  tool: "Führt ein lokales CLI-Skript oder Python-Tool deterministisch mit Output-Cap aus.",
  output: "Finaler Ausgabeknoten. Liefert das Endergebnis des Agent-Workflows zurück.",
};