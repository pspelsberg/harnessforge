import {Handle, Position} from "@xyflow/react";
import type {NodeProps} from "@xyflow/react";
import {useGraphStore, type NodeType} from "./graphStore";
import {NODE_LABELS, NODE_COLORS} from "./nodeRegistry";

export type ForgeVisualData = {
  type: NodeType;
  label?: string;
  color?: string;
  status?: "idle" | "running" | "success" | "error";
  sourceHandles?: string[];
  targetHandles?: string[];
};

export function ForgeNode(props: NodeProps) {
  const data = props.data as unknown as ForgeVisualData;
  const color = data.color || NODE_COLORS[data.type] || "#38bdf8";
  const sourceHandles = data.sourceHandles ?? ["default"];
  const targetHandles = data.targetHandles ?? ["default"];
  const isSelected = Boolean(props.selected);
  const isMultiHandle = sourceHandles.length > 1;

  const getHandleColor = (id: string, defaultColor: string) => {
    if (id === "true") return "#10b981";
    if (id === "false") return "#ef4444";
    if (id === "fallback") return "#f59e0b";
    return defaultColor;
  };

  const handles = (type: "source" | "target", values: string[]) =>
    values.map((id, index) => {
      const handleColor = getHandleColor(id, color);
      const topPercent = isMultiHandle && type === "source"
        ? `${((index + 1) / (values.length + 1)) * 100}%`
        : `${((index + 1) / (values.length + 1)) * 100}%`;

      return (
        <div key={`${type}-${id}`}>
          <Handle
            id={id === "default" ? undefined : id}
            type={type}
            position={type === "source" ? Position.Right : Position.Left}
            title={id === "default" ? undefined : `${id} route`}
            style={{
              top: topPercent,
              background: handleColor,
              width: 10,
              height: 10,
              border: "2px solid #0b0f17",
            }}
          />
          {type === "source" && values.length > 1 && (
            <span
              style={{
                position: "absolute",
                right: 14,
                top: topPercent,
                transform: "translateY(-50%)",
                fontSize: "0.62rem",
                fontWeight: 700,
                lineHeight: 1,
                color: id === "true" ? "#34d399" : id === "false" ? "#f87171" : id === "fallback" ? "#fbbf24" : "#94a3b8",
                background: "rgba(11, 15, 23, 0.95)",
                padding: "2px 6px",
                borderRadius: 4,
                pointerEvents: "none",
                userSelect: "none",
                letterSpacing: "0.02em",
                border: `1px solid ${
                  id === "true"
                    ? "rgba(52, 211, 153, 0.4)"
                    : id === "false"
                    ? "rgba(248, 113, 113, 0.4)"
                    : "rgba(251, 191, 36, 0.4)"
                }`,
                boxShadow: "0 2px 6px rgba(0,0,0,0.5)",
              }}
            >
              {id}
            </span>
          )}
        </div>
      );
    });

  const nodeMinHeight = isMultiHandle ? 96 : 50;
  const nodeMinWidth = isMultiHandle ? 230 : 170;

  return (
    <article
      aria-label={`${NODE_LABELS[data.type]} node`}
      className={`forge-node forge-node-${data.status || "idle"}`}
      style={{
        borderLeftWidth: "4px",
        borderLeftColor: color,
        position: "relative",
        minHeight: nodeMinHeight,
        minWidth: nodeMinWidth,
        display: "flex",
        flexDirection: "column",
        justifyContent: isMultiHandle ? "flex-start" : "center",
        padding: isMultiHandle ? "12px 14px" : "10px 14px",
        borderColor: isSelected ? "#f59e0b" : undefined,
        boxShadow: isSelected ? "0 0 16px rgba(245, 158, 11, 0.4)" : undefined,
      }}
    >
      {handles("target", targetHandles)}
      <div
        className="forge-node-header"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          margin: 0,
          maxWidth: isMultiHandle ? "calc(100% - 62px)" : "100%",
        }}
      >
        <strong className="forge-node-title" style={{ color, fontSize: "0.85rem", whiteSpace: "nowrap" }}>
          {data.label || NODE_LABELS[data.type]}
        </strong>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span className="forge-node-status" style={{ fontSize: "0.68rem" }}>{data.status || "idle"}</span>
          {isSelected && (
            <button
              aria-label={`delete node ${props.id}`}
              title="Knoten löschen"
              style={{
                background: "rgba(239, 68, 68, 0.2)",
                border: "1px solid rgba(239, 68, 68, 0.5)",
                color: "#fca5a5",
                borderRadius: 4,
                cursor: "pointer",
                padding: "2px 6px",
                fontSize: "0.75rem",
                lineHeight: 1,
                boxShadow: "0 2px 6px rgba(0,0,0,0.4)",
              }}
              onClick={(e) => {
                e.stopPropagation();
                useGraphStore.getState().removeNode(props.id);
              }}
            >
              🗑️
            </button>
          )}
        </div>
      </div>
      {handles("source", sourceHandles)}
    </article>
  );
}
