// src/xstate_statemachine/inspector/frontend/src/components/edges/TransitionEdge.tsx
import {
  EdgeLabelRenderer,
  EdgeProps,
  getSmoothStepPath,
  getStraightPath,
  Position,
} from "reactflow";

/**
 * Orthogonal edge that:
 * - draws a straight line when nodes are aligned horizontally/vertically
 * - otherwise draws a 90° step path (borderRadius = 0 for hard corners)
 * - optionally shows a label (skipped for initial edges)
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
  const EPS = 0.5; // tolerance for "aligned" detection with snapped positions

  const isHorizontal =
    Math.abs(sourceY - targetY) < EPS &&
    (sourcePosition === Position.Left || sourcePosition === Position.Right) &&
    (targetPosition === Position.Left || targetPosition === Position.Right);

  const isVertical =
    Math.abs(sourceX - targetX) < EPS &&
    (sourcePosition === Position.Top || sourcePosition === Position.Bottom) &&
    (targetPosition === Position.Top || targetPosition === Position.Bottom);

  const clampTopY: number | undefined = data?.clampTopY;
  const clampLeftX: number | undefined = data?.clampLeftX;
  const clampRightX: number | undefined = data?.clampRightX;
  const clampBottomY: number | undefined = data?.clampBottomY;

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

  const [edgePath, labelX, labelY] =
    isHorizontal || isVertical
      ? getStraightPath({ sourceX, sourceY, targetX, targetY })
      : getSmoothStepPath({
          sourceX,
          sourceY,
          targetX,
          targetY,
          sourcePosition,
          targetPosition,
          borderRadius: 0, // hard 90° corners
          // Keep the elbow within the span between nodes to avoid overshooting the wrapper
          centerX: Math.max(Math.min(midX, Math.max(sourceX, targetX)), Math.min(sourceX, targetX)),
          centerY: Math.max(Math.min(midY, Math.max(sourceY, targetY)), Math.min(sourceY, targetY)),
          offset: 14, // tighter elbows so edges stay closer to nodes
        });

  const isInitial = !!data?.isInitial;
  const label = data?.label as string | undefined;
  const labelYClamped = clampTopY ? Math.max(labelY, clampTopY + 8) : labelY;

  return (
    <>
      {!isInitial && label && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan absolute pointer-events-none"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelYClamped}px)`,
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
        fill="none"
        stroke="hsl(var(--foreground))"
        strokeWidth={2}
        markerEnd={markerEnd}
        shapeRendering="geometricPrecision"
      />
    </>
  );
};
