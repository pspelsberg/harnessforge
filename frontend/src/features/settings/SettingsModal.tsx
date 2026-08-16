import {useState, useEffect} from "react";
import {
  fetchProviderSettings,
  saveProviderSettings,
  type ProviderSettingsResponse,
} from "./settingsApi";
import {getSessionToken, setSessionToken} from "../../shared/session";

export function SettingsModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [settings, setSettings] = useState<ProviderSettingsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Key form inputs
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [mistralKey, setMistralKey] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("http://127.0.0.1:11434");

  // Visibility toggles
  const [showAnthropic, setShowAnthropic] = useState(false);
  const [showOpenai, setShowOpenai] = useState(false);
  const [showOpenrouter, setShowOpenrouter] = useState(false);
  const [showGemini, setShowGemini] = useState(false);
  const [showMistral, setShowMistral] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      const load = async () => {
        let token = getSessionToken();
        if (!token) {
          try {
            const tokenRes = await fetch("/api/session/token");
            if (tokenRes.ok) {
              const tokenData = await tokenRes.json();
              if (tokenData?.token) {
                token = tokenData.token;
                setSessionToken(token);
              }
            }
          } catch {
            // fallback
          }
        }
        try {
          const data = await fetchProviderSettings(token);
          setSettings(data);
          setOllamaUrl(data.ollama.url || "http://127.0.0.1:11434");
        } catch (err) {
          // If token was outdated, try refreshing once from local session endpoint
          try {
            const tokenRes = await fetch("/api/session/token");
            if (tokenRes.ok) {
              const tokenData = await tokenRes.json();
              if (tokenData?.token) {
                setSessionToken(tokenData.token);
                const data = await fetchProviderSettings(tokenData.token);
                setSettings(data);
                setOllamaUrl(data.ollama.url || "http://127.0.0.1:11434");
                return;
              }
            }
          } catch {
            // ignore
          }
          setError(err instanceof Error ? err.message : "Fehler beim Laden der Einstellungen");
        } finally {
          setLoading(false);
        }
      };
      void load();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    const payload: Record<string, string> = {};
    if (anthropicKey.trim()) payload.anthropic_api_key = anthropicKey.trim();
    if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim();
    if (openrouterKey.trim()) payload.openrouter_api_key = openrouterKey.trim();
    if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();
    if (mistralKey.trim()) payload.mistral_api_key = mistralKey.trim();
    if (ollamaUrl.trim()) payload.ollama_url = ollamaUrl.trim();

    try {
      let token = getSessionToken();
      if (!token) {
        const tokenRes = await fetch("/api/session/token");
        if (tokenRes.ok) {
          const tokenData = await tokenRes.json();
          token = tokenData?.token || "";
          setSessionToken(token);
        }
      }
      const updated = await saveProviderSettings(payload, token);
      setSettings(updated);
      setAnthropicKey("");
      setOpenaiKey("");
      setOpenrouterKey("");
      setGeminiKey("");
      setMistralKey("");
      setSuccessMessage("✅ API-Keys erfolgreich verschlüsselt/gesichert in .env abgelegt!");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Speichern der Schlüssel");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Settings Modal"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        backdropFilter: "blur(5px)",
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
          border: "1.5px solid #334155",
          borderRadius: 12,
          width: "100%",
          maxWidth: 660,
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.9), 0 0 24px rgba(56, 189, 248, 0.15)",
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
                width: 38,
                height: 38,
                borderRadius: 8,
                background: "rgba(56, 189, 248, 0.15)",
                border: "1px solid rgba(56, 189, 248, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.2rem",
              }}
            >
              ⚙️
            </div>
            <div>
              <h2 style={{margin: 0, fontSize: "1.15rem", fontWeight: 700, color: "#f8fafc"}}>
                Einstellungen & API-Schlüssel
              </h2>
              <p style={{margin: 0, fontSize: "0.75rem", color: "#94a3b8"}}>
                Sichere Schlüssel-Verwaltung (Local Trust Mode & Restricted <code>.env</code>)
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

        {/* Security Notice */}
        <div
          style={{
            background: "rgba(15, 23, 42, 0.8)",
            border: "1px solid rgba(56, 189, 248, 0.25)",
            borderRadius: 8,
            padding: "10px 14px",
            fontSize: "0.75rem",
            color: "#94a3b8",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <div style={{color: "#38bdf8", fontWeight: 700, display: "flex", alignItems: "center", gap: 6}}>
            🛡️ Sicherheits- & Datenschutz-Garantie
          </div>
          <div>
            Schlüssel werden <strong>niemals im Browser-Speicher</strong> oder in Graph-Dateien abgelegt.
            Sie verbleiben rein im Speicher des lokalen Backends und werden mit <code>chmod 0600</code> (nur dein OS-Benutzer) in der <code>.env</code> gesichert.
          </div>
        </div>

        {loading && <div style={{color: "#94a3b8", fontSize: "0.85rem"}}>Lade Provider-Status...</div>}

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

        {successMessage && (
          <div
            role="status"
            style={{
              background: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              color: "#6ee7b7",
              padding: "8px 12px",
              borderRadius: 6,
              fontSize: "0.78rem",
            }}
          >
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSave} style={{display: "flex", flexDirection: "column", gap: 14}}>
          {/* Anthropic Claude */}
          <div style={{background: "#090d16", border: "1px solid #1e293b", borderRadius: 8, padding: 12}}>
            <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6}}>
              <label htmlFor="anthropic-key-input" style={{fontWeight: 700, fontSize: "0.82rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: 6}}>
                🟣 Anthropic Claude (Claude Sonnet 5, Opus 5)
              </label>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontWeight: 600,
                  background: settings?.anthropic.configured ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.1)",
                  color: settings?.anthropic.configured ? "#34d399" : "#94a3b8",
                  border: `1px solid ${settings?.anthropic.configured ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.2)"}`,
                }}
              >
                {settings?.anthropic.configured ? `🟢 Aktiv (${settings.anthropic.masked})` : "⚪ Nicht gesetzt"}
              </span>
            </div>
            <div style={{display: "flex", gap: 6}}>
              <input
                id="anthropic-key-input"
                aria-label="anthropic api key"
                type={showAnthropic ? "text" : "password"}
                placeholder={settings?.anthropic.configured ? "Neuen Schlüssel eingeben zum Überschreiben..." : "sk-ant-api03-..."}
                value={anthropicKey}
                onChange={e => setAnthropicKey(e.target.value)}
                style={{
                  flex: 1,
                  background: "#0b0f17",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  padding: "6px 10px",
                  color: "#f8fafc",
                  fontSize: "0.82rem",
                }}
              />
              <button
                type="button"
                className="forge-btn"
                style={{padding: "6px 10px"}}
                onClick={() => setShowAnthropic(!showAnthropic)}
                title={showAnthropic ? "Verbergen" : "Anzeigen"}
              >
                {showAnthropic ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {/* OpenAI */}
          <div style={{background: "#090d16", border: "1px solid #1e293b", borderRadius: 8, padding: 12}}>
            <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6}}>
              <label htmlFor="openai-key-input" style={{fontWeight: 700, fontSize: "0.82rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: 6}}>
                🟢 OpenAI (GPT-5.6 Luna, Terra, Sol)
              </label>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontWeight: 600,
                  background: settings?.openai.configured ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.1)",
                  color: settings?.openai.configured ? "#34d399" : "#94a3b8",
                  border: `1px solid ${settings?.openai.configured ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.2)"}`,
                }}
              >
                {settings?.openai.configured ? `🟢 Aktiv (${settings.openai.masked})` : "⚪ Nicht gesetzt"}
              </span>
            </div>
            <div style={{display: "flex", gap: 6}}>
              <input
                id="openai-key-input"
                aria-label="openai api key"
                type={showOpenai ? "text" : "password"}
                placeholder={settings?.openai.configured ? "Neuen Schlüssel eingeben zum Überschreiben..." : "sk-proj-..."}
                value={openaiKey}
                onChange={e => setOpenaiKey(e.target.value)}
                style={{
                  flex: 1,
                  background: "#0b0f17",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  padding: "6px 10px",
                  color: "#f8fafc",
                  fontSize: "0.82rem",
                }}
              />
              <button
                type="button"
                className="forge-btn"
                style={{padding: "6px 10px"}}
                onClick={() => setShowOpenai(!showOpenai)}
                title={showOpenai ? "Verbergen" : "Anzeigen"}
              >
                {showOpenai ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {/* OpenRouter */}
          <div style={{background: "#090d16", border: "1px solid #1e293b", borderRadius: 8, padding: 12}}>
            <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6}}>
              <label htmlFor="openrouter-key-input" style={{fontWeight: 700, fontSize: "0.82rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: 6}}>
                🔵 OpenRouter Gateway
              </label>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontWeight: 600,
                  background: settings?.openrouter.configured ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.1)",
                  color: settings?.openrouter.configured ? "#34d399" : "#94a3b8",
                  border: `1px solid ${settings?.openrouter.configured ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.2)"}`,
                }}
              >
                {settings?.openrouter.configured ? `🟢 Aktiv (${settings.openrouter.masked})` : "⚪ Nicht gesetzt"}
              </span>
            </div>
            <div style={{display: "flex", gap: 6}}>
              <input
                id="openrouter-key-input"
                aria-label="openrouter api key"
                type={showOpenrouter ? "text" : "password"}
                placeholder={settings?.openrouter.configured ? "Neuen Schlüssel eingeben zum Überschreiben..." : "sk-or-v1-..."}
                value={openrouterKey}
                onChange={e => setOpenrouterKey(e.target.value)}
                style={{
                  flex: 1,
                  background: "#0b0f17",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  padding: "6px 10px",
                  color: "#f8fafc",
                  fontSize: "0.82rem",
                }}
              />
              <button
                type="button"
                className="forge-btn"
                style={{padding: "6px 10px"}}
                onClick={() => setShowOpenrouter(!showOpenrouter)}
                title={showOpenrouter ? "Verbergen" : "Anzeigen"}
              >
                {showOpenrouter ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {/* Google Gemini */}
          <div style={{background: "#090d16", border: "1px solid #1e293b", borderRadius: 8, padding: 12}}>
            <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6}}>
              <label htmlFor="gemini-key-input" style={{fontWeight: 700, fontSize: "0.82rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: 6}}>
                🔴 Google Gemini (Gemini 3.7 Flash)
              </label>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontWeight: 600,
                  background: settings?.gemini.configured ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.1)",
                  color: settings?.gemini.configured ? "#34d399" : "#94a3b8",
                  border: `1px solid ${settings?.gemini.configured ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.2)"}`,
                }}
              >
                {settings?.gemini.configured ? `🟢 Aktiv (${settings.gemini.masked})` : "⚪ Nicht gesetzt"}
              </span>
            </div>
            <div style={{display: "flex", gap: 6}}>
              <input
                id="gemini-key-input"
                aria-label="gemini api key"
                type={showGemini ? "text" : "password"}
                placeholder={settings?.gemini.configured ? "Neuen Schlüssel eingeben zum Überschreiben..." : "AIzaSy..."}
                value={geminiKey}
                onChange={e => setGeminiKey(e.target.value)}
                style={{
                  flex: 1,
                  background: "#0b0f17",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  padding: "6px 10px",
                  color: "#f8fafc",
                  fontSize: "0.82rem",
                }}
              />
              <button
                type="button"
                className="forge-btn"
                style={{padding: "6px 10px"}}
                onClick={() => setShowGemini(!showGemini)}
                title={showGemini ? "Verbergen" : "Anzeigen"}
              >
                {showGemini ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {/* Mistral AI */}
          <div style={{background: "#090d16", border: "1px solid #1e293b", borderRadius: 8, padding: 12}}>
            <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6}}>
              <label htmlFor="mistral-key-input" style={{fontWeight: 700, fontSize: "0.82rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: 6}}>
                🟠 Mistral AI (Codestral, Mistral Large 2, Nemo)
              </label>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontWeight: 600,
                  background: settings?.mistral.configured ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.1)",
                  color: settings?.mistral.configured ? "#34d399" : "#94a3b8",
                  border: `1px solid ${settings?.mistral.configured ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.2)"}`,
                }}
              >
                {settings?.mistral.configured ? `🟢 Aktiv (${settings.mistral.masked})` : "⚪ Nicht gesetzt"}
              </span>
            </div>
            <div style={{display: "flex", gap: 6}}>
              <input
                id="mistral-key-input"
                aria-label="mistral api key"
                type={showMistral ? "text" : "password"}
                placeholder={settings?.mistral.configured ? "Neuen Schlüssel eingeben zum Überschreiben..." : "mistral-api-key..."}
                value={mistralKey}
                onChange={e => setMistralKey(e.target.value)}
                style={{
                  flex: 1,
                  background: "#0b0f17",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  padding: "6px 10px",
                  color: "#f8fafc",
                  fontSize: "0.82rem",
                }}
              />
              <button
                type="button"
                className="forge-btn"
                style={{padding: "6px 10px"}}
                onClick={() => setShowMistral(!showMistral)}
                title={showMistral ? "Verbergen" : "Anzeigen"}
              >
                {showMistral ? "🙈" : "👁️"}
              </button>
            </div>
          </div>

          {/* Ollama Local */}
          <div style={{background: "#090d16", border: "1px solid #1e293b", borderRadius: 8, padding: 12}}>
            <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6}}>
              <label htmlFor="ollama-url-input" style={{fontWeight: 700, fontSize: "0.82rem", color: "#f8fafc", display: "flex", alignItems: "center", gap: 6}}>
                🦙 Ollama Local Host (Qwen 2.5, DeepSeek R1)
              </label>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontWeight: 600,
                  background: settings?.ollama.connected ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.1)",
                  color: settings?.ollama.connected ? "#34d399" : "#fbbf24",
                  border: `1px solid ${settings?.ollama.connected ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                }}
              >
                {settings?.ollama.connected ? "🟢 Verbunden (127.0.0.1:11434)" : "🟡 Offline / Nicht gestartet"}
              </span>
            </div>
            <input
              id="ollama-url-input"
              aria-label="ollama base url"
              type="text"
              value={ollamaUrl}
              onChange={e => setOllamaUrl(e.target.value)}
              style={{
                width: "100%",
                background: "#0b0f17",
                border: "1px solid #1e293b",
                borderRadius: 6,
                padding: "6px 10px",
                color: "#f8fafc",
                fontSize: "0.82rem",
              }}
            />
          </div>

          {/* Footer Actions */}
          <div style={{display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8}}>
            <button type="button" className="forge-btn" onClick={onClose} disabled={saving}>
              Schließen
            </button>
            <button
              type="submit"
              className="forge-btn forge-btn-success"
              disabled={saving}
              style={{
                padding: "8px 18px",
                fontSize: "0.85rem",
                fontWeight: 700,
                boxShadow: "0 0 14px rgba(16, 185, 129, 0.35)",
              }}
            >
              {saving ? "⏳ Speichere..." : "💾 Einstellungen in .env Speichern"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
