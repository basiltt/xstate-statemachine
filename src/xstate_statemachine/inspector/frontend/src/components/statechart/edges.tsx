import React from "react";
import { EdgeLabelRenderer, EdgeProps } from "reactflow";

type TransitionEdgeData = {
  isInitial?: boolean;
  uiActive?: boolean;
  label?: string;

  // Waypoints produced by the router (grid–snapped, rectilinear)
  waypoints?: { x: number; y: number }[];

  // Wrapper clamps (auto-injected)
  clampTopY?: number;
  clampLeftX?: number;
  clampRightX?: number;
  clampBottomY?: number;

  // Optional lane offset applied by the router for parallel edges
  laneOffset?: number;

  // Corner radius for rounded 90° corners
  cornerR?: number;
};

function clampPoint(
  p: { x: number; y: number },
  clamp?: { top?: number; left?: number; right?: number; bottom?: number },
) {
  return {
    x: Math.min(Math.max(p.x, clamp?.left ?? -Infinity), clamp?.right ?? Infinity),
    y: Math.min(Math.max(p.y, clamp?.top ?? -Infinity), clamp?.bottom ?? Infinity),
  };
}

function pathFromWaypoints(pts: { x: number; y: number }[], r = 6): string {
  if (!pts.length) return "";
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;
  // Build orthogonal polyline with rounded corners via small arcs
  const d: string[] = [];
  d.push(`M ${pts[0].x} ${pts[0].y}`);
  for (let i = 1; i < pts.length; i++) {
    const p0 = pts[i - 1];
    const p1 = pts[i];
    const isStraight = p0.x === p1.x || p0.y === p1.y;
    if (i === pts.length - 1 || !isStraight) {
      // Corner between p0 -> p1 and p1 -> p2
      if (i < pts.length - 1) {
        const p2 = pts[i + 1];
        // direction vectors
        const dx1 = Math.sign(p1.x - p0.x);
        const dy1 = Math.sign(p1.y - p0.y);
        const dx2 = Math.sign(p2.x - p1.x);
        const dy2 = Math.sign(p2.y - p1.y);

        const cut1 = {
          x: p1.x - dx1 * r,
          y: p1.y - dy1 * r,
        };
        const cut2 = {
          x: p1.x + dx2 * r,
          y: p1.y + dy2 * r,
        };

        // line up to first cut
        d.push(`L ${cut1.x} ${cut1.y}`);

        // arc from cut1 -> cut2 (quarter circle)
        // Using absolute arc command: rx ry 0 0 sweep x y
        // Sweep is 0/1 depending on turn direction
        const sweep =
          (dx1 === 1 && dy2 === 1) ||
          (dy1 === -1 && dx2 === -1) ||
          (dx1 === -1 && dy2 === -1) ||
          (dy1 === 1 && dx2 === 1)
            ? 1
            : 0;
        d.push(`A ${r} ${r} 0 0 ${sweep} ${cut2.x} ${cut2.y}`);
      } else {
        // last segment into p1
        d.push(`L ${p1.x} ${p1.y}`);
      }
    } else {
      // straight segment
      d.push(`L ${p1.x} ${p1.y}`);
    }
  }
  return d.join(" ");
}

export const TransitionEdge = ({ id, markerEnd, data }: EdgeProps<TransitionEdgeData>) => {
  const {
    clampTopY,
    clampLeftX,
    clampRightX,
    clampBottomY,
    waypoints,
    isInitial,
    uiActive,
    label,
    cornerR = 6,
    laneOffset = 0,
  } = data ?? {};

  // If router didn’t provide waypoints yet, don’t render an edge shape;
  // RF will render a fallback preview while dragging.
  if (!waypoints || waypoints.length === 0) {
    return null;
  }

  const clamp = {
    top: clampTopY,
    left: clampLeftX,
    right: clampRightX,
    bottom: clampBottomY,
  };

  // Apply clamps and optional lane offset (for parallel edges)
  const pts = waypoints.map((p) => {
    const c = clampPoint(p, clamp);
    return {
      x: c.x + (laneOffset && p.y === c.y ? laneOffset : 0),
      y: c.y + (laneOffset && p.x === c.x ? laneOffset : 0),
    };
  });

  const d = pathFromWaypoints(pts, cornerR);

  const style: React.CSSProperties = {
    strokeWidth: uiActive ? 2.2 : 2,
    stroke: "hsl(var(--foreground))",
    fill: "none",
    opacity: isInitial ? 0.7 : uiActive ? 0.95 : 0.9,
    strokeDasharray: isInitial ? "6 4" : undefined,
  };

  // Edge label placed at the middle waypoint (approx)
  const midIndex = Math.floor(pts.length / 2);
  const lx = pts[midIndex]?.x ?? pts[0].x;
  const ly = pts[midIndex]?.y ?? pts[0].y;

  return (
    <>
      {label && !isInitial && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan absolute pointer-events-none"
            style={{
              transform: `translate(-50%, -50%) translate(${lx}px, ${ly}px)`,
            }}
          >
            <div className="px-2 py-0.5 rounded-full text-xs bg-background border shadow-sm">
              {label}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
      <path id={id} d={d} markerEnd={markerEnd} style={style} />
    </>
  );
};
