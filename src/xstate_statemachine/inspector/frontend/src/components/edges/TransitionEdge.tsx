// src/xstate_statemachine/inspector/frontend/src/components/edges/TransitionEdge.tsx
import { EdgeLabelRenderer, EdgeProps, Position } from "reactflow";

// Manhattan-style connector with optional lane offsets and bounding clamp
function orthogonalPath(options: {
  sx: number;
  sy: number;
  tx: number;
  ty: number;
  sp: Position;
  bounds?: { left?: number; right?: number; top?: number; bottom?: number };
  laneAxis?: "x" | "y";
  laneOffset?: number;
}) {
  const { sx, sy, tx, ty, sp, bounds, laneAxis, laneOffset = 0 } = options;
  const left = bounds?.left ?? -Infinity;
  const right = bounds?.right ?? Infinity;
  const top = bounds?.top ?? -Infinity;
  const bottom = bounds?.bottom ?? Infinity;

  const pts: { x: number; y: number }[] = [{ x: sx, y: sy }];
  const sameX = Math.abs(sx - tx) < 0.5;
  const sameY = Math.abs(sy - ty) < 0.5;

  if (sameX || sameY) {
    // direct segment
    pts.push({ x: tx, y: ty });
  } else {
    // L path - choose orientation based on source side
    if (sp === Position.Left || sp === Position.Right) {
      const ix = Math.max(left, Math.min(tx, right));
      const iy = Math.max(top, Math.min(sy, bottom));
      pts.push({ x: ix, y: iy });
    } else {
      const ix = Math.max(left, Math.min(sx, right));
      const iy = Math.max(top, Math.min(ty, bottom));
      pts.push({ x: ix, y: iy });
    }
    pts.push({ x: tx, y: ty });
  }

  // Apply lane offset to intermediate points
  if (laneAxis === "x") {
    pts.forEach((p, i) => {
      if (i > 0 && i < pts.length - 1) p.x = Math.max(left, Math.min(p.x + laneOffset, right));
    });
  } else if (laneAxis === "y") {
    pts.forEach((p, i) => {
      if (i > 0 && i < pts.length - 1) p.y = Math.max(top, Math.min(p.y + laneOffset, bottom));
    });
  }

  const d = `M ${pts.map((p) => `${p.x} ${p.y}`).join(" L ")}`;

  // label position - middle of last segment
  let lx: number;
  let ly: number;
  if (pts.length === 2) {
    lx = (sx + tx) / 2;
    ly = (sy + ty) / 2;
  } else {
    const a = pts[pts.length - 2];
    const b = pts[pts.length - 1];
    lx = (a.x + b.x) / 2;
    ly = (a.y + b.y) / 2;
  }

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
  markerEnd,
  data,
}: EdgeProps) => {
  const clampTopY: number | undefined = data?.clampTopY;
  const clampLeftX: number | undefined = data?.clampLeftX;
  const clampRightX: number | undefined = data?.clampRightX;
  const clampBottomY: number | undefined = data?.clampBottomY;
  const laneAxis: "x" | "y" | undefined = (data as any)?.laneAxis;
  const laneOffset: number = (data as any)?.laneOffset ?? 0;
  const isInitial = !!data?.isInitial;
  const isActive = !!data?.uiActive;
  const label = data?.label as string | undefined;
  const { d: edgePath, lx, ly } = orthogonalPath({
    sx: sourceX,
    sy: sourceY,
    tx: targetX,
    ty: targetY,
    sp: sourcePosition,
    bounds: { left: clampLeftX, right: clampRightX, top: clampTopY, bottom: clampBottomY },
    laneAxis,
    laneOffset,
  });

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
