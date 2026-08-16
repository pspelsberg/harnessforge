import {useState, useEffect} from "react";
import {FlowCanvas} from "../features/canvas/FlowCanvas";
import {useGraphStore, importGraphJson, type NodeType} from "../features/canvas/graphStore";
import {RunHistory} from "../features/observability/RunHistory";
import {deleteRun} from "../features/observability/runApi";
import {TraceDrawer, type TraceEvent} from "../features/observability/TraceDrawer";
import {Inspector} from "../features/inspector/Inspector";
import {WorkspaceFiles} from "../features/inspector/WorkspaceFiles";
import {WsClient} from "../features/observability/wsClient";
import {requestProviderApproval} from "../features/inspector/approvalApi";
import {downloadGraph} from "../features/canvas/downloadGraph";
import {saveGraph} from "../features/canvas/graphApi";
import {runGraph} from "../features/canvas/runApi";
import {exportGraph} from "../features/export_bundle/exportApi";
import {getSessionToken, setSessionToken, clearSessionToken} from "../shared/session";
import {NODE_LABELS, NODE_COLORS, NODE_DESCRIPTIONS} from "../features/canvas/nodeRegistry";
import {LlmBuilderModal} from "../features/canvas/LlmBuilderModal";
import {SettingsModal} from "../features/settings/SettingsModal";

const STARTER_TEMPLATES = {
  reactLoop: {
    name: "Minimal ReAct Loop",
    nodes: [
      {
        id: "start-1",
        type: "start",
        position: {x: 80, y: 150},
        data: {
          config: {input_key: "code_task", default_query: "Fixe den fehlerhaften Testlauf im Workspace"},
          ui: {status: "idle"},
        },
      },
      {
        id: "llm-1",
        type: "llm",
        position: {x: 320, y: 150},
        data: {
          config: {
            model: "qwen2.5-coder:32b",
            temperature: 0.2,
            node_prompt:
              "Du bist ein ReAct Coding Agent. Analysiere den Test-Fehler und erstelle einen Fix:\n\nTest-Fehler:\n{test_output}\n\nWorkspace-Kontext:\n{workspace_files}\n\nGeneriere die Korrektur direkt als lauffähigen Code.",
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "tool-1",
        type: "tool",
        position: {x: 600, y: 150},
        data: {
          config: {
            path: "pytest",
            args: ["tests/", "-q", "--tb=short"],
            max_output_bytes: 51200,
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "loop-1",
        type: "loop",
        position: {x: 880, y: 150},
        data: {
          config: {
            condition_type: "equals",
            key: "exit_code",
            value: "0",
            max_iterations: 3,
            fallback: "out-1",
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "out-1",
        type: "output",
        position: {x: 1180, y: 150},
        data: {
          config: {format: "markdown", return_fields: ["code_fix", "exit_code", "iterations"]},
          ui: {status: "idle"},
        },
      },
    ],
    edges: [
      {id: "e1", source: "start-1", target: "llm-1"},
      {id: "e2", source: "llm-1", target: "tool-1"},
      {id: "e3", source: "tool-1", target: "loop-1"},
      {id: "e4", source: "loop-1", target: "out-1", sourceHandle: "true"},
      {id: "e5", source: "loop-1", target: "llm-1", sourceHandle: "false"},
      {id: "e6", source: "loop-1", target: "out-1", sourceHandle: "fallback"},
    ],
  },
  ragBot: {
    name: "LanceDB RAG Assistant",
    nodes: [
      {
        id: "start-1",
        type: "start",
        position: {x: 80, y: 150},
        data: {
          config: {input_key: "user_query", default_query: "Wie funktioniert die WorkspaceBoundary in HarnessForge?"},
          ui: {status: "idle"},
        },
      },
      {
        id: "rag-1",
        type: "rag",
        position: {x: 320, y: 150},
        data: {
          config: {
            path: ".lancedb",
            table: "docs",
            top_k: 5,
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "llm-1",
        type: "llm",
        position: {x: 600, y: 150},
        data: {
          config: {
            model: "gpt-5.6-luna",
            temperature: 0.3,
            node_prompt:
              "Du bist ein technischer Dokumentations-Assistent.\n\nKontext aus LanceDB Vektordatenbank:\n{rag_context}\n\nBenutzerfrage: {user_query}\n\nBeantworte die Frage präzise anhand des gegebenen Kontexts mit Codebeispielen.",
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "out-1",
        type: "output",
        position: {x: 880, y: 150},
        data: {
          config: {format: "markdown", target_sink: "chat_stream"},
          ui: {status: "idle"},
        },
      },
    ],
    edges: [
      {id: "e1", source: "start-1", target: "rag-1"},
      {id: "e2", source: "rag-1", target: "llm-1"},
      {id: "e3", source: "llm-1", target: "out-1"},
    ],
  },
  codingFixer: {
    name: "Self-Healing Coding Agent",
    nodes: [
      {
        id: "start-1",
        type: "start",
        position: {x: 80, y: 150},
        data: {
          config: {input_key: "task", default_query: "Implementiere den Rate-Limiter und führe Sicherheitsprüfungen durch"},
          ui: {status: "idle"},
        },
      },
      {
        id: "llm-1",
        type: "llm",
        position: {x: 320, y: 150},
        data: {
          config: {
            model: "claude-sonnet-5",
            temperature: 0.1,
            node_prompt:
              "Du bist ein Senior Systems Engineer. Implementiere die Anforderung oder repariere gefundene Testfehler.\n\nAufgabe: {task}\nBisherige Versuche: {history}\nLetzter Testfehler: {test_output}\n\nGib den vollständigen, sauberen TypeScript/Python Code aus.",
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "tool-1",
        type: "tool",
        position: {x: 600, y: 150},
        data: {
          config: {
            path: "pytest",
            args: ["tests/unit/", "-q", "--maxfail=1"],
            max_output_bytes: 51200,
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "loop-1",
        type: "loop",
        position: {x: 880, y: 150},
        data: {
          config: {
            condition_type: "equals",
            key: "exit_code",
            value: "0",
            max_iterations: 5,
            fallback: "out-1",
          },
          ui: {status: "idle"},
        },
      },
      {
        id: "out-1",
        type: "output",
        position: {x: 1180, y: 150},
        data: {
          config: {format: "markdown", return_fields: ["code", "test_report", "attempts"]},
          ui: {status: "idle"},
        },
      },
    ],
    edges: [
      {id: "e1", source: "start-1", target: "llm-1"},
      {id: "e2", source: "llm-1", target: "tool-1"},
      {id: "e3", source: "tool-1", target: "loop-1"},
      {id: "e4", source: "loop-1", target: "out-1", sourceHandle: "true"},
      {id: "e5", source: "loop-1", target: "llm-1", sourceHandle: "false"},
      {id: "e6", source: "loop-1", target: "out-1", sourceHandle: "fallback"},
    ],
  },
};

export function App() {
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [activeLeftTab, setActiveLeftTab] = useState<"palette" | "files" | "history">("palette");
  const [activeBottomTab, setActiveBottomTab] = useState<"trace" | "status">("trace");
  const [sessionInput, setSessionInput] = useState(getSessionToken());
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [graphName, setGraphName] = useState("Minimal ReAct Loop");
  const [isLlmBuilderOpen, setIsLlmBuilderOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const {
    setGraph,
    reviewOnly,
    setReviewOnly,
    nodes,
    selectedNodeId,
    externalDataflowActivated,
    updateConfig,
  } = useGraphStore();

  useEffect(() => {
    fetch("/api/session/token")
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.token) {
          setSessionToken(data.token);
          setSessionInput(data.token);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    useGraphStore.getState().recover();
    const keydown = (event: KeyboardEvent) => {
      const state = useGraphStore.getState();
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        state.undo();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
        event.preventDefault();
        state.redo();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d") {
        event.preventDefault();
        if (state.selectedNodeId) state.duplicateNode(state.selectedNodeId);
      } else if ((event.key === "Delete" || event.key === "Backspace") && (state.selectedNodeId || state.selectedEdgeId)) {
        event.preventDefault();
        state.deleteSelected();
      }
    };
    window.addEventListener("keydown", keydown);

    const client = new WsClient(`ws://${location.host}/ws`, getSessionToken(), event => {
      setEvents(previous => [...previous, {type: event.type, payload: event.payload || {}}].slice(-200));
      const nodeId = event.payload?.node_id;
      if (typeof nodeId === "string") {
        const status =
          event.type.endsWith("running") || event.type.endsWith("queued")
            ? "running"
            : event.type.endsWith("succeeded")
            ? "success"
            : event.type.endsWith("failed")
            ? "error"
            : null;
        if (status) useGraphStore.getState().setNodeStatus(nodeId, status);
      }
    });
    client.connect();

    return () => {
      window.removeEventListener("keydown", keydown);
      client.close();
    };
  }, []);

  const add = (type: NodeType) => {
    const id = `${type}-${Date.now()}`;
    const node = {id, type, position: {x: 200 + nodes.length * 40, y: 150 + nodes.length * 30}, data: {config: {}, ui: {}}};
    const state = useGraphStore.getState();
    if (state.nodes.length >= 50) {
      setError("Node limit reached");
      return;
    }
    setGraph([...state.nodes, node], state.edges);
  };

  const loadTemplate = (key: keyof typeof STARTER_TEMPLATES) => {
    const tmpl = STARTER_TEMPLATES[key];
    setGraphName(tmpl.name);
    setGraph(tmpl.nodes as never[], tmpl.edges as never[]);
    setReviewOnly(false);
    setError(null);
  };

  const token = () => getSessionToken();
  const payload = () => ({
    schema_version: "1" as const,
    id: "local",
    name: graphName || "My Agent Harness",
    workspace_path: ".",
    nodes,
    edges: useGraphStore.getState().edges,
    settings: {review_only: reviewOnly, external_dataflow_activated: externalDataflowActivated},
  });

  const save = async () => {
    try {
      await saveGraph("graph.forge.json", payload(), token());
      setError(null);
    } catch {
      setError("Save failed");
    }
  };

  const run = async () => {
    try {
      await runGraph(payload(), "", token());
      setError(null);
    } catch {
      setError("Run failed");
    }
  };

  const exportBundle = async () => {
    try {
      await exportGraph(payload(), "bundle", token());
      setError(null);
    } catch {
      setError("Export failed");
    }
  };

  const load = (raw: string) => {
    try {
      const graph = importGraphJson(raw);
      if (graph.name) setGraphName(graph.name);
      setGraph(graph.nodes, graph.edges);
      setReviewOnly(true);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid graph");
    }
  };

  const nodeTypes: NodeType[] = ["start", "llm", "rag", "loop", "reducer", "tool", "output"];

  return (
    <main className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section" style={{display: "flex", alignItems: "center", gap: 8}}>
          <img src="/assets/logo.jpg" alt="HarnessForge logo" className="brand-logo" />
          <span className="brand-title">HarnessForge</span>
          <span style={{color: "#475569", margin: "0 2px"}}>•</span>
          <span className={`mode-badge ${reviewOnly ? "review" : "active"}`}>
            {reviewOnly ? "Review mode" : "Active"}
          </span>
          <span style={{color: "#475569", margin: "0 2px"}}>•</span>
          <input
            aria-label="graph name"
            value={graphName}
            onChange={e => setGraphName(e.target.value)}
            placeholder="Graph Name..."
            title="Klicken zum Umbenennen des Graphs"
            style={{
              background: "transparent",
              border: "1px solid transparent",
              borderRadius: 4,
              color: "#f8fafc",
              fontWeight: 700,
              fontSize: "0.85rem",
              padding: "2px 6px",
              outline: "none",
              width: `${Math.max(180, Math.min(380, (graphName.length + 3) * 9))}px`,
              transition: "all 0.15s ease",
            }}
            onFocus={e => {
              e.currentTarget.style.background = "#0b0f17";
              e.currentTarget.style.borderColor = "#38bdf8";
            }}
            onBlur={e => {
              e.currentTarget.style.background = "transparent";
              e.currentTarget.style.borderColor = "transparent";
            }}
          />
        </div>

        {/* Global Toolbar */}
        <div className="toolbar-actions">
          <button className={`forge-btn ${reviewOnly ? "forge-btn-success" : ""}`} onClick={() => setReviewOnly(!reviewOnly)}>
            {reviewOnly ? "Activate" : "Review"}
          </button>
          <button className="forge-btn" onClick={save}>
            Save
          </button>
          <button className="forge-btn" onClick={() => downloadGraph(payload())}>
            Download JSON
          </button>
          <button className="forge-btn forge-btn-primary" onClick={run} disabled={reviewOnly}>
            ▶ Run
          </button>
          <button className="forge-btn" onClick={exportBundle} disabled={reviewOnly}>
            📦 Export
          </button>
          <button
            className="forge-btn forge-btn-primary"
            style={{
              background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
              borderColor: "#38bdf8",
              display: "flex",
              alignItems: "center",
              gap: 5,
              boxShadow: "0 0 12px rgba(56, 189, 248, 0.35)",
            }}
            onClick={() => setIsLlmBuilderOpen(true)}
          >
            🤖 AI Builder
          </button>
          <button
            className="forge-btn"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              borderColor: "#334155",
            }}
            onClick={() => setIsSettingsOpen(true)}
            title="API-Schlüssel & Provider-Einstellungen"
          >
            ⚙️ Settings
          </button>

          <div style={{width: 1, height: 24, background: "#1e293b", margin: "0 4px"}} />

          {/* Session Token */}
          <div style={{display: "flex", alignItems: "center", gap: 6}}>
            <label style={{fontSize: "0.75rem", color: "#94a3b8", display: "flex", alignItems: "center", gap: 6}}>
              🔑 Session token
              <input
                type="password"
                aria-label="session token"
                className="forge-input"
                style={{width: 130}}
                placeholder="Token..."
                value={sessionInput}
                onChange={e => {
                  setSessionInput(e.target.value);
                  try {
                    setSessionToken(e.target.value);
                    setError(null);
                  } catch {
                    setError("Invalid session token");
                  }
                }}
              />
            </label>
            <button
              className="forge-btn"
              style={{padding: "4px 8px", fontSize: "0.75rem"}}
              onClick={() => {
                clearSessionToken();
                setSessionInput("");
                setError("Session cleared");
              }}
            >
              Clear
            </button>
          </div>

          <label className="forge-btn" style={{cursor: "pointer", fontSize: "0.78rem"}}>
            📂 Import
            <input
              type="file"
              accept=".json,.forge.json"
              style={{display: "none"}}
              onChange={e => {
                const file = e.target.files?.[0];
                if (file) file.text().then(load);
              }}
            />
          </label>
        </div>
      </header>

      {/* Alert Error Message */}
      {error && (
        <div
          role="alert"
          style={{
            position: "absolute",
            top: 64,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 100,
            background: "rgba(239, 68, 68, 0.95)",
            color: "#fff",
            padding: "8px 18px",
            borderRadius: 8,
            boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
            fontSize: "0.82rem",
            fontWeight: 600,
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* Main 3-Column Studio */}
      <div className="app-studio">
        {/* Left Sidebar */}
        <aside className="left-sidebar">
          <div className="sidebar-tabs">
            <div
              className={`sidebar-tab ${activeLeftTab === "palette" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("palette")}
            >
              Nodes
            </div>
            <div
              className={`sidebar-tab ${activeLeftTab === "files" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("files")}
            >
              Files
            </div>
            <div
              className={`sidebar-tab ${activeLeftTab === "history" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("history")}
            >
              Runs
            </div>
          </div>

          {activeLeftTab === "palette" && (
            <nav aria-label="Node palette" className="palette-items">
              <div style={{fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700, margin: "4px 0"}}>
                Drag or Click to Add
              </div>
              {nodeTypes.map(type => (
                <div
                  key={type}
                  className="palette-card"
                  draggable
                  onDragStart={event => event.dataTransfer.setData("application/x-harnessforge-node", type)}
                  onClick={() => add(type)}
                >
                  <div
                    className="palette-card-icon"
                    style={{
                      background: `rgba(${
                        NODE_COLORS[type] === "#f59e0b"
                          ? "245, 158, 11"
                          : NODE_COLORS[type] === "#38bdf8"
                          ? "56, 189, 248"
                          : "16, 185, 129"
                      }, 0.2)`,
                      color: NODE_COLORS[type],
                    }}
                  >
                    {type.slice(0, 2).toUpperCase()}
                  </div>
                  <div style={{flex: 1}}>
                    <div style={{fontWeight: 600, fontSize: "0.82rem"}}>{NODE_LABELS[type]}</div>
                    <div style={{fontSize: "0.7rem", color: "#64748b"}}>{type} node</div>
                  </div>
                  <div
                    className="palette-info-btn"
                    onClick={e => e.stopPropagation()}
                  >
                    ℹ
                    <div className="palette-tooltip">
                      <strong style={{display: "block", color: NODE_COLORS[type], marginBottom: 4, fontSize: "0.78rem"}}>
                        {NODE_LABELS[type]}
                      </strong>
                      {NODE_DESCRIPTIONS[type]}
                    </div>
                  </div>
                </div>
              ))}

              <div style={{marginTop: 16, borderTop: "1px solid #1e293b", paddingTop: 12}}>
                <div style={{fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700, marginBottom: 8}}>
                  ⚡ Starter Templates & AI
                </div>
                <button
                  className="forge-btn"
                  style={{
                    width: "100%",
                    textAlign: "left",
                    justifyContent: "flex-start",
                    marginBottom: 8,
                    background: "rgba(56, 189, 248, 0.12)",
                    borderColor: "rgba(56, 189, 248, 0.4)",
                    color: "#38bdf8",
                    fontWeight: 700,
                  }}
                  onClick={() => setIsLlmBuilderOpen(true)}
                >
                  ✨ Prompt to Graph (AI Builder)
                </button>
                <button
                  className="forge-btn"
                  style={{width: "100%", textAlign: "left", justifyContent: "flex-start", marginBottom: 6}}
                  onClick={() => loadTemplate("reactLoop")}
                >
                  🔄 Minimal ReAct Loop
                </button>
                <button
                  className="forge-btn"
                  style={{width: "100%", textAlign: "left", justifyContent: "flex-start", marginBottom: 6}}
                  onClick={() => loadTemplate("ragBot")}
                >
                  📚 LanceDB RAG QA
                </button>
                <button
                  className="forge-btn"
                  style={{width: "100%", textAlign: "left", justifyContent: "flex-start"}}
                  onClick={() => loadTemplate("codingFixer")}
                >
                  🛠️ Self-Healing Coding Agent
                </button>
              </div>
            </nav>
          )}

          {activeLeftTab === "files" && (
            <div style={{padding: 12, overflowY: "auto", flex: 1}}>
              <WorkspaceFiles token={token()} onSelect={file => setError(`Selected ${file}`)} />
            </div>
          )}

          {activeLeftTab === "history" && (
            <div style={{padding: 12, overflowY: "auto", flex: 1}}>
              <RunHistory
                token={token()}
                onSelect={id => setError(`Selected run ${id}`)}
                onDelete={id => {
                  void deleteRun(id, token())
                    .then(() => setError(null))
                    .catch(() => setError("Delete failed"));
                }}
              />
            </div>
          )}
        </aside>

        {/* Center Canvas */}
        <div className="canvas-wrapper">
          <FlowCanvas />
        </div>

        {/* Right Inspector */}
        <Inspector
          node={nodes.find(node => node.id === selectedNodeId)}
          onConfigChange={config => {
            if (selectedNodeId) updateConfig(selectedNodeId, config);
          }}
          onActivateDataflow={() => useGraphStore.getState().setExternalDataflow(true)}
          onRequestApproval={bindings => {
            const node = nodes.find(item => item.id === selectedNodeId);
            return requestProviderApproval(
              (node?.data.config.provider as Record<string, unknown>) || {},
              bindings,
              token()
            ).then(result => result.approval_fingerprint);
          }}
        />
      </div>

      {/* Bottom Drawer */}
      <footer className={`bottom-drawer ${!isDrawerOpen ? "collapsed" : ""}`}>
        <div
          className="drawer-header"
          style={{cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between"}}
          onClick={() => setIsDrawerOpen(!isDrawerOpen)}
        >
          <div className="drawer-tabs">
            <div
              className={`drawer-tab ${activeBottomTab === "trace" ? "active" : ""}`}
              onClick={e => {
                e.stopPropagation();
                setActiveBottomTab("trace");
                setIsDrawerOpen(true);
              }}
            >
              📡 Live Trace & Events ({events.length})
            </div>
          </div>
          <button
            className="forge-btn"
            style={{padding: "2px 8px", fontSize: "0.72rem", display: "flex", alignItems: "center", gap: 4}}
            onClick={e => {
              e.stopPropagation();
              setIsDrawerOpen(!isDrawerOpen);
            }}
          >
            {isDrawerOpen ? "▼ Einklappen" : "▲ Ausklappen"}
          </button>
        </div>
        <div className="drawer-content" style={{display: isDrawerOpen ? "flex" : "none", flexDirection: "column", flex: 1, overflow: "hidden"}}>
          <TraceDrawer events={events} onClear={() => setEvents([])} />
        </div>
      </footer>

      {/* AI Agent Architect / LLM Builder Modal */}
      <LlmBuilderModal
        isOpen={isLlmBuilderOpen}
        onClose={() => setIsLlmBuilderOpen(false)}
        onApplyGraph={graph => {
          if (graph.name) setGraphName(graph.name);
          setGraph(graph.nodes, graph.edges);
          setReviewOnly(true);
          setError(null);
        }}
      />

      {/* Settings & Secure API Keys Vault Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </main>
  );
}
