// src/xstate_statemachine/inspector/frontend/src/components/edges/TransitionEdge.tsx
import { EdgeLabelRenderer, EdgeProps, getSmoothStepPath, Position } from "reactflow";
// Smooth step connector with clamped control center and optional lane offsets
function smoothPath(options: {
  sx: number;
  sy: number;
  tx: number;
  ty: number;
  sp: Position;
  tp: Position;
  centerBias?: { x?: number; y?: number };
  bounds?: { left?: number; right?: number; top?: number; bottom?: number };
}) {
  const { sx, sy, tx, ty, sp, tp, centerBias, bounds } = options;
  const left = bounds?.left ?? -Infinity;
  const right = bounds?.right ?? Infinity;
  const top = bounds?.top ?? -Infinity;
  const bottom = bounds?.bottom ?? Infinity;

  const sSide = sp;
  const horizontalFirst = sSide === Position.Left || sSide === Position.Right;

  const rawCenterX = (sx + tx) / 2 + (centerBias?.x ?? 0);
  const rawCenterY = (sy + ty) / 2 + (centerBias?.y ?? 0);
  const centerX = Math.max(left, Math.min(rawCenterX, right));
  const centerY = Math.max(top, Math.min(rawCenterY, bottom));

  const offset = horizontalFirst ? 22 : 18; // gentle curvature like xstate viz
  const [d, lx, ly] = getSmoothStepPath({
    sourceX: sx,
    sourceY: sy,
    targetX: tx,
    targetY: ty,
    sourcePosition: sp,
    targetPosition: tp,
    borderRadius: 10,
    centerX,
    centerY,
    offset,
  });
  return { d, lx, ly };
}

/**
 * Orthogonal edge that:
 * - stays within the wrapper inner bounds (no touching borders)
 * - never goes under the header/sub-header (clamped by top bound)
 * - draws straight lines when aligned; otherwise a 90°-elbow Manhattan path
 */
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
}: EdgeProps) => {
  const waypoints = (data as any)?.waypoints as { x: number; y: number }[] | undefined;
  const clampTopY: number | undefined = data?.clampTopY;
  const clampLeftX: number | undefined = data?.clampLeftX;
  const clampRightX: number | undefined = data?.clampRightX;
  const clampBottomY: number | undefined = data?.clampBottomY;
  const laneAxis: "x" | "y" | undefined = (data as any)?.laneAxis;
  const laneOffset: number = (data as any)?.laneOffset ?? 0;
  const isInitial = !!data?.isInitial;
  const isActive = !!data?.uiActive;
  const label = data?.label as string | undefined;
  const bias = laneAxis === "x" ? { x: laneOffset } : laneAxis === "y" ? { y: laneOffset } : {};
  let edgePath = "";
  let lx = 0,
    ly = 0;
  if (waypoints && waypoints.length >= 2) {
    // Build an orthogonal path from waypoints; clamp a middle label point
    const pts = waypoints;
    const midIdx = Math.floor(pts.length / 2);
    const mid = pts[midIdx];
    lx = Math.min(Math.max(mid.x, clampLeftX ?? -Infinity), clampRightX ?? Infinity);
    ly = clampTopY ? Math.max(mid.y, clampTopY + 8) : mid.y;
    edgePath =
      `M ${pts[0].x},${pts[0].y} ` +
      pts
        .slice(1)
        .map((p) => `L ${p.x},${p.y}`)
        .join(" ");
  } else {
    const r = smoothPath({
      sx: sourceX,
      sy: sourceY,
      tx: targetX,
      ty: targetY,
      sp: sourcePosition,
      tp: targetPosition,
      centerBias: bias,
      bounds: { left: clampLeftX, right: clampRightX, top: clampTopY, bottom: clampBottomY },
    });
    edgePath = r.d;
    lx = r.lx;
    ly = r.ly;
  }
  // Apply lane offset to label too (respecting bounds)

  const stroke = isInitial
    ? "hsl(var(--foreground) / 0.45)"
    : isActive
      ? "hsl(var(--foreground) / 0.9)"
      : "hsl(var(--foreground) / 0.55)";
  const strokeWidth = isActive ? 2.2 : 2;
  const style: React.CSSProperties = {
    stroke,
    strokeWidth,
    fill: "none",
  };
  const lxShift = laneAxis === "x" ? laneOffset : 0;
  const lyShift = laneAxis === "y" ? laneOffset : 0;
  const labelYClamped = clampTopY ? Math.max(ly + lyShift, clampTopY + 8) : ly + lyShift;
  const labelXClamped = Math.min(
    Math.max(lx + lxShift, clampLeftX ?? -Infinity),
    clampRightX ?? Infinity,
  );

  return (
    <>
      {!isInitial && label && (
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

      <path
        id={id}
        d={edgePath}
        style={style}
        markerEnd={markerEnd}
        shapeRendering="geometricPrecision"
      />
    </>
  );
};
