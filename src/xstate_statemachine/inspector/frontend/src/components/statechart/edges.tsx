// src/components/statechart/edges.tsx
import React from "react";
import { EdgeLabelRenderer, EdgeProps, getStraightPath, Position } from "reactflow";

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

function manhattanPath(options: {
  sx: number;
  sy: number;
  tx: number;
  ty: number;
  sp: Position;
  tp: Position;
  bounds?: { left?: number; right?: number; top?: number; bottom?: number };
}) {
  const { sx, sy, tx, ty, sp, tp, bounds } = options;
  const left = bounds?.left ?? -Infinity;
  const right = bounds?.right ?? Infinity;
  const top = bounds?.top ?? -Infinity;
  const bottom = bounds?.bottom ?? Infinity;

  // Clamp endpoints into bounds so edges never cross header/wrapper
  const Sx = Math.min(Math.max(sx, left), right);
  const Sy = Math.min(Math.max(sy, top), bottom);
  const Tx = Math.min(Math.max(tx, left), right);
  const Ty = Math.min(Math.max(ty, top), bottom);

  const isHoriz =
    Math.abs(Sy - Ty) < 0.5 &&
    (sp === Position.Left || sp === Position.Right) &&
    (tp === Position.Left || tp === Position.Right);

  const isVert =
    Math.abs(Sx - Tx) < 0.5 &&
    (sp === Position.Top || sp === Position.Bottom) &&
    (tp === Position.Top || tp === Position.Bottom);

  if (isHoriz || isVert) {
    const [d, lx, ly] = getStraightPath({ sourceX: Sx, sourceY: Sy, targetX: Tx, targetY: Ty });
    return { d, lx, ly };
  }

  // Choose routing order based on handle orientation
  const horizontalFirst = sp === Position.Left || sp === Position.Right;

  if (horizontalFirst) {
    const midX = Math.min(Math.max((Sx + Tx) / 2, left), right);
    const p = `M ${Sx},${Sy} L ${midX},${Sy} L ${midX},${Ty} L ${Tx},${Ty}`;
    const lx = midX;
    const ly = (Sy + Ty) / 2;
    return { d: p, lx, ly };
  } else {
    const midY = Math.min(Math.max((Sy + Ty) / 2, top), bottom);
    const p = `M ${Sx},${Sy} L ${Sx},${midY} L ${Tx},${midY} L ${Tx},${Ty}`;
    const lx = (Sx + Tx) / 2;
    const ly = midY;
    return { d: p, lx, ly };
  }
}

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

  const {
    d: edgePath,
    lx,
    ly,
  } = manhattanPath({
    sx: sourceX,
    sy: sourceY,
    tx: targetX,
    ty: targetY,
    sp: sourcePosition,
    tp: targetPosition,
    bounds: { left: clampLeftX, right: clampRightX, top: clampTopY, bottom: clampBottomY },
  });

  const isActive = Boolean(data?.uiActive);
  const isInitial = Boolean(data?.isInitial);
  const label = data?.label;

  const style: React.CSSProperties = {
    strokeWidth: isActive ? 2.5 : 2,
    stroke: "hsl(var(--foreground))",
    opacity: isActive ? 0.95 : 0.85,
    ...(isInitial ? { strokeDasharray: "6 4", opacity: 0.65 } : null),
  };

  const labelYClamped = clampTopY ? Math.max(ly, clampTopY + 8) : ly;
  const labelXClamped = Math.min(Math.max(lx, clampLeftX ?? -Infinity), clampRightX ?? Infinity);

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
