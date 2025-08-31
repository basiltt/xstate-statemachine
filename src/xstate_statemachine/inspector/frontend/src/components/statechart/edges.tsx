// src/xstate_statemachine/inspector/frontend/src/components/statechart/edges.tsx
import React from "react";
import { EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from "reactflow";

type TransitionEdgeData = {
  /** Mark edge as an initial transition (render dashed). */
  isInitial?: boolean;
  /** Highlight edge when its source is active/next. */
  uiActive?: boolean;
  /** Optional label text. */
  label?: string;
  /** Inner clamps injected by useDiagram to keep edges within wrapper and below header */
  clampTopY?: number;
  clampLeftX?: number;
  clampRightX?: number;
  clampBottomY?: number;
};

export const TransitionEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data,
}: EdgeProps<TransitionEdgeData>) => {
  const { clampTopY, clampLeftX, clampRightX, clampBottomY } = data ?? {};

  const midXRaw = (sourceX + targetX) / 2;
  const midYRaw = (sourceY + targetY) / 2;
  const midX = Math.max(
    clampLeftX ?? -Infinity,
    Math.min(midXRaw, clampRightX ?? Infinity, Math.max(sourceX, targetX)),
  );
  const midY = Math.max(
    clampTopY ?? -Infinity,
    Math.min(midYRaw, clampBottomY ?? Infinity, Math.max(sourceY, targetY)),
  );

  // Adjust elbow bias to respect vertical dominance to reduce overlap when sources are above/below
  const verticalDominant = Math.abs(sourceY - targetY) > Math.abs(sourceX - targetX) * 0.75;
  const offset = verticalDominant ? 26 : 18;

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 8,
    centerX: Math.max(Math.min(midX, Math.max(sourceX, targetX)), Math.min(sourceX, targetX)),
    centerY: Math.max(Math.min(midY, Math.max(sourceY, targetY)), Math.min(sourceY, targetY)),
    offset,
  });

  const isActive = Boolean(data?.uiActive);
  const isInitial = Boolean(data?.isInitial);
  const label = data?.label;

  const style: React.CSSProperties = {
    strokeWidth: isActive ? 2.2 : 2,
    stroke: "hsl(var(--foreground))",
    opacity: isActive ? 0.95 : 0.9,
    ...(isInitial ? { strokeDasharray: "6 4", opacity: 0.7 } : null),
  };

  const labelYClamped = clampTopY ? Math.max(labelY, clampTopY + 8) : labelY;
  const labelXClamped = Math.min(
    Math.max(labelX, clampLeftX ?? -Infinity),
    clampRightX ?? Infinity,
  );

  return (
    <>
      {label && !isInitial && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan absolute pointer-events-none"
            style={{
              transform: `translate(-50%, -50%) translate(${labelXClamped}px, ${labelYClamped}px)`,
            }}
          >
            <div className="px-2 py-0.5 rounded-full text-xs bg-background border shadow-sm">
              {label}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}

      <path id={id} d={edgePath} fill="none" markerEnd={markerEnd} style={style} />
    </>
  );
};
