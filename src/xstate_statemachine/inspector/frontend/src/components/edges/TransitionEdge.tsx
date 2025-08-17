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
          borderRadius: 0, // 0 => hard 90° corners; raise slightly for rounded elbows
        });

  const isInitial = !!data?.isInitial;
  const label = data?.label as string | undefined;

  return (
    <>
      {!isInitial && label && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan absolute pointer-events-none"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
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
