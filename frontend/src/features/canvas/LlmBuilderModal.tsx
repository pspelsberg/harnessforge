import {useState} from "react";
import {generateGraphWithLlm, type GeneratedGraphResponse} from "./llmBuilderApi";
import {getSessionToken} from "../../shared/session";

const BUILDER_PRESETS = [
  {
    title: "🔄 ReAct Loop mit Pytest",
    prompt: "Erstelle einen autonomen ReAct-Agenten mit Qwen 2.5 Coder, der Pytest-Tests in tests/ ausführt und bei Fehlschlägen den Code bis zu 4x überarbeitet.",
  },
  {
    title: "📚 LanceDB RAG Pipeline",
    prompt: "Erstelle eine RAG-Pipeline mit LanceDB Vektordatenbank auf dem docs/ Ordner und einem LLM für präzise technische Dokumentations-Antworten.",
  },
  {
    title: "🛠️ Self-Healing Coding Agent",
    prompt: "Erstelle einen Coding-Agenten mit Claude Sonnet 5, der Funktionen implementiert, Tests durchführt und bei Fehlern automatisch Refactorings anwendet.",
  },
  {
    title: "⚡ Multi-LLM Planer & Critic",
    prompt: "Erstelle eine Kette aus zwei LLMs: Erst ein Planer-LLM zur Architekturanalyse, dann ein Coder-LLM zur Code-Generierung.",
  },
];

const ARCHITECT_MODELS = [
  {id: "codestral-latest", label: "codestral-latest (Mistral Codestral Native)"},
  {id: "mistral-large-latest", label: "mistral-large-latest (Mistral Large 2)"},
  {id: "mistral-medium-latest", label: "mistral-medium-latest (Mistral Medium 3.5)"},
  {id: "mistral-small-latest", label: "mistral-small-latest (Mistral Small 3/4)"},
  {id: "ministral-8b-latest", label: "ministral-8b-latest (Ministral 8B)"},
  {id: "open-mistral-nemo", label: "open-mistral-nemo (Mistral Nemo)"},
  {id: "qwen2.5-coder:32b", label: "qwen2.5-coder:32b (Local / Ollama)"},
  {id: "deepseek-r1:32b", label: "deepseek-r1:32b (Local Reasoning)"},
  {id: "claude-sonnet-5", label: "claude-sonnet-5 (Anthropic Claude 5)"},
  {id: "claude-opus-5", label: "claude-opus-5 (Anthropic Opus 5)"},
  {id: "gpt-5.6-luna", label: "gpt-5.6-luna (OpenAI Fast Agentic)"},
  {id: "gpt-5.6-terra", label: "gpt-5.6-terra (OpenAI GPT-5.6)"},
  {id: "gemini-3.7-flash", label: "gemini-3.7-flash (Google Gemini 3)"},
];

export function LlmBuilderModal({
  isOpen,
  onClose,
  onApplyGraph,
}: {
  isOpen: boolean;
  onClose: () => void;
  onApplyGraph: (graph: GeneratedGraphResponse) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("qwen2.5-coder:32b");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Bitte gib eine Beschreibung für den gewünschten Agenten-Graph ein.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const graph = await generateGraphWithLlm(prompt, model, getSessionToken());
      onApplyGraph(graph);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Generieren des Graphs");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="AI Graph Architect Modal"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#0d131f",
          border: "1.5px solid #38bdf8",
          borderRadius: 12,
          width: "100%",
          maxWidth: 620,
          boxShadow: "0 16px 40px rgba(0, 0, 0, 0.9), 0 0 24px rgba(56, 189, 248, 0.25)",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{display: "flex", alignItems: "center", justifyContent: "space-between"}}>
          <div style={{display: "flex", alignItems: "center", gap: 10}}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: "rgba(56, 189, 248, 0.15)",
                border: "1px solid rgba(56, 189, 248, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.2rem",
              }}
            >
              🤖
            </div>
            <div>
              <h2 style={{margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "#f8fafc"}}>
                AI Agent Architect (LLM Builder)
              </h2>
              <p style={{margin: 0, fontSize: "0.75rem", color: "#94a3b8"}}>
                Prompt to Graph: Beschreibe deinen Workflow, das LLM baut & verdrahtet die Knoten.
              </p>
            </div>
          </div>
          <button
            className="forge-btn"
            style={{padding: "4px 8px", fontSize: "0.85rem"}}
            onClick={onClose}
            aria-label="Schließen"
          >
            ✕
          </button>
        </div>

        {/* Architect Model Selection */}
        <label style={{display: "flex", flexDirection: "column", gap: 6, fontSize: "0.78rem", color: "#94a3b8", fontWeight: 600}}>
          <span>🧠 Architekt-Modell (Inferenz)</span>
          <select
            aria-label="architect model selector"
            value={model}
            onChange={e => setModel(e.target.value)}
            style={{
              background: "#0b0f17",
              border: "1px solid #1e293b",
              borderRadius: 6,
              padding: "8px 10px",
              color: "#f8fafc",
              fontSize: "0.82rem",
            }}
          >
            {ARCHITECT_MODELS.map(m => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>

        {/* Prompt Input */}
        <label style={{display: "flex", flexDirection: "column", gap: 6, fontSize: "0.78rem", color: "#94a3b8", fontWeight: 600}}>
          <span>💬 Was soll dein Agent tun? (Prompt)</span>
          <textarea
            aria-label="agent workflow description"
            placeholder="z. B. Baue einen autonomen ReAct-Agenten, der Python-Dateien mit Pytest testet und bei Fehlern den Code bis zu 5x überarbeitet..."
            rows={4}
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            style={{
              background: "#0b0f17",
              border: "1px solid #1e293b",
              borderRadius: 6,
              padding: "10px 12px",
              color: "#f8fafc",
              fontSize: "0.85rem",
              fontFamily: "inherit",
              resize: "vertical",
              outline: "none",
            }}
          />
        </label>

        {/* Quick Inspiration Chips */}
        <div>
          <div style={{fontSize: "0.7rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700, marginBottom: 6}}>
            💡 Schnellauswahl & Inspiration:
          </div>
          <div style={{display: "flex", flexWrap: "wrap", gap: 6}}>
            {BUILDER_PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="forge-btn"
                style={{
                  padding: "4px 8px",
                  fontSize: "0.72rem",
                  background: prompt === p.prompt ? "#1e293b" : "#111827",
                  borderColor: prompt === p.prompt ? "#38bdf8" : "#1e293b",
                }}
                onClick={() => setPrompt(p.prompt)}
              >
                {p.title}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div
            role="alert"
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#fca5a5",
              padding: "8px 12px",
              borderRadius: 6,
              fontSize: "0.78rem",
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {/* Actions */}
        <div style={{display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8}}>
          <button className="forge-btn" onClick={onClose} disabled={loading}>
            Abbrechen
          </button>
          <button
            className="forge-btn forge-btn-primary"
            onClick={handleGenerate}
            disabled={loading}
            style={{
              padding: "8px 18px",
              fontSize: "0.85rem",
              fontWeight: 700,
              background: loading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
              boxShadow: "0 0 16px rgba(56, 189, 248, 0.4)",
            }}
          >
            {loading ? "⏳ Generiere Agenten-Graph..." : "✨ Graph Generieren & Anwenden"}
          </button>
        </div>
      </div>
    </div>
  );
}
