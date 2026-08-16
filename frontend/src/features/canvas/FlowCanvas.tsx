import {useCallback, useMemo} from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Node,
  type Edge,
  type NodeChange,
  applyNodeChanges,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {useGraphStore, validateGraph, type ForgeEdge, type ForgeNode, type NodeType} from "./graphStore";
import {NODE_LABELS, NODE_COLORS} from "./nodeRegistry";
import {ForgeNode as ForgeNodeView} from "./ForgeNode";
import {StartNode, LLMNode, RAGNode, LoopNode, ReducerNode, ToolNode, OutputNode} from "./customNodes";
import {ForgeEdge as ForgeEdgeView} from "./ForgeEdge";

const nodeTypes = {
  default: ForgeNodeView,
  start: StartNode,
  llm: LLMNode,
  rag: RAGNode,
  loop: LoopNode,
  reducer: ReducerNode,
  tool: ToolNode,
  output: OutputNode,
};
const edgeTypes = {default: ForgeEdgeView};
const NODE_TYPES = new Set<NodeType>(["start", "llm", "rag", "loop", "reducer", "tool", "output"]);

function CanvasSurface({nodes, edges}: {nodes: ForgeNode[]; edges: ForgeEdge[]}) {
  const {screenToFlowPosition} = useReactFlow();
  const {
    setSelected,
    setSelectedEdge,
    removeEdge,
    removeNode,
    updatePosition,
    connectNodes,
    addNode,
    selectedEdgeId,
  } = useGraphStore();

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/x-harnessforge-node") as NodeType;
      if (!NODE_TYPES.has(type)) return;
      const node = addNode(type);
      if (!node) return;
      const position = screenToFlowPosition({x: event.clientX, y: event.clientY});
      updatePosition(node.id, {x: position.x, y: position.y});
    },
    [addNode, screenToFlowPosition, updatePosition]
  );

  const viewNodes = useMemo(
    () =>
      nodes.map(node => ({
        ...node,
        data: {...node.data, label: NODE_LABELS[node.type], color: NODE_COLORS[node.type]},
      })),
    [nodes]
  );

  const viewEdges: Edge[] = useMemo(
    () =>
      edges.map(edge => ({
        ...edge,
        type: "default",
        selected: edge.id === selectedEdgeId,
      })),
    [edges, selectedEdgeId]
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          updatePosition(change.id, change.position);
        }
      }
    },
    [updatePosition]
  );

  return (
    <ReactFlow
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      nodes={viewNodes as unknown as Node[]}
      edges={viewEdges}
      onNodesChange={onNodesChange}
      onDrop={onDrop}
      onDragOver={event => event.preventDefault()}
      onNodeClick={(_, node) => setSelected(String(node.id))}
      onEdgeClick={(_, edge: Edge) => setSelectedEdge(String(edge.id))}
      onPaneClick={() => {
        setSelected(null);
        setSelectedEdge(null);
      }}
      onEdgesDelete={(deletedEdges: Edge[]) => deletedEdges.forEach(e => removeEdge(String(e.id)))}
      onNodesDelete={(deletedNodes: Node[]) => deletedNodes.forEach(n => removeNode(String(n.id)))}
      onNodeDragStop={(_, node) =>
        updatePosition(String(node.id), {x: Number(node.position.x), y: Number(node.position.y)})
      }
      onConnect={connection => {
        if (connection.source && connection.target)
          connectNodes(connection.source, connection.target, connection.sourceHandle || undefined);
      }}
      fitView
      style={{background: "#0b0f17"}}
    >
      <Background color="#1e293b" gap={20} size={1.5} />
      <Controls style={{background: "#151d2a", border: "1px solid #334155", borderRadius: 8}} />
      <MiniMap
        nodeColor={node => NODE_COLORS[node.type as NodeType] || "#38bdf8"}
        maskColor="rgba(11, 15, 23, 0.7)"
        style={{background: "#111827", border: "1px solid #1e293b", borderRadius: 8}}
      />
    </ReactFlow>
  );
}

export function FlowCanvas() {
  const {nodes, edges} = useGraphStore();
  const issues = useMemo(() => validateGraph(nodes, edges), [nodes, edges]);

  const decorated = useMemo(() => {
    const invalid = new Set(issues.filter(issue => issue.severity === "error" && issue.nodeId).map(issue => issue.nodeId));
    const warning = new Set(issues.filter(issue => issue.severity === "warning" && issue.nodeId).map(issue => issue.nodeId));
    return nodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        status: invalid.has(node.id) ? "error" : warning.has(node.id) ? "running" : node.data.ui.status,
      },
    }));
  }, [nodes, issues]);

  return (
    <ReactFlowProvider>
      <section aria-label="graph canvas" style={{width: "100%", height: "100%", position: "relative"}}>
        {issues.length > 0 && (
          <aside
            role="status"
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              zIndex: 10,
              maxWidth: 360,
              background: "rgba(17, 24, 39, 0.92)",
              backdropFilter: "blur(8px)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: 8,
              padding: "8px 12px",
              boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            }}
          >
            {issues.map((issue, index) => (
              <p
                key={`${issue.nodeId ?? issue.message}-${index}`}
                style={{
                  margin: "3px 0",
                  fontSize: "0.75rem",
                  color: issue.severity === "error" ? "#fca5a5" : "#fde047",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span>{issue.severity === "error" ? "⚠️" : "ℹ️"}</span>
                {issue.message}
              </p>
            ))}
          </aside>
        )}
        <CanvasSurface nodes={decorated} edges={edges} />
      </section>
    </ReactFlowProvider>
  );
}
