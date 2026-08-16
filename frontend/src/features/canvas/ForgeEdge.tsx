import {BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps} from "@xyflow/react";
import {useGraphStore} from "./graphStore";

export function ForgeEdge({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  data,
  selected,
}: EdgeProps) {
  const [path, labelX, labelY] = getBezierPath({sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition});
  const active = Boolean((data as {active?: boolean} | undefined)?.active);
  const gradientId = `forge-gradient-${id.replace(/[^A-Za-z0-9_-]/g, "_")}`;

  return (
    <>
      <svg aria-hidden="true" style={{position: "absolute", width: 0, height: 0, pointerEvents: "none"}}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={selected ? "#f59e0b" : "#38bdf8"} />
            <stop offset="100%" stopColor={selected ? "#ef4444" : "#818cf8"} />
          </linearGradient>
        </defs>
      </svg>
      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke: selected ? "#f59e0b" : active ? "#fb923c" : "#38bdf8",
          strokeWidth: selected ? 3.5 : 2,
          strokeDasharray: active ? "8 4" : undefined,
          filter: selected ? "drop-shadow(0 0 8px #f59e0b)" : "drop-shadow(0 0 4px rgba(56, 189, 248, 0.3))",
          cursor: "pointer",
        }}
      />
      {active && (
        <circle
          className="forge-edge-particle"
          r="3.5"
          fill="#fcd34d"
          style={{offsetPath: `path('${path}')`, offsetDistance: "0%"}}
          aria-hidden="true"
        />
      )}
      {selected && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
              zIndex: 1000,
            }}
            className="nodrag nopan"
          >
            <button
              aria-label={`delete edge ${id}`}
              title="Verbindung löschen"
              style={{
                background: "#151d2a",
                border: "1.5px solid #ef4444",
                color: "#fca5a5",
                borderRadius: "50%",
                width: 24,
                height: 24,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                fontSize: "0.7rem",
                boxShadow: "0 0 12px rgba(239, 68, 68, 0.6)",
                transition: "transform 0.15s, background 0.15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.25)")}
              onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
              onClick={e => {
                e.stopPropagation();
                useGraphStore.getState().removeEdge(id);
              }}
            >
              🗑️
            </button>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
