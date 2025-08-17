// src/xstate_statemachine/inspector/frontend/src/components/statechart/edges.tsx

import { BaseEdge, EdgeProps, getSmoothStepPath } from "reactflow";

export const TransitionEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  data,
}: EdgeProps) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    borderRadius: 16,
  });

  const isInitial = data?.isInitial;

  // A small dot for the initial state transition start
  const initialPath = `M ${sourceX} ${sourceY} L ${sourceX} ${sourceY}`;

  return (
    <>
      {isInitial && (
        <circle
          cx={sourceX}
          cy={sourceY}
          r={6}
          className="fill-foreground stroke-background"
          strokeWidth={2}
        />
      )}
      <BaseEdge
        id={id}
        path={isInitial ? initialPath : edgePath}
        markerEnd={markerEnd}
        style={{
          strokeWidth: 2,
          stroke: "hsl(var(--foreground))",
          opacity: 0.8,
        }}
      />
    </>
  );
};
