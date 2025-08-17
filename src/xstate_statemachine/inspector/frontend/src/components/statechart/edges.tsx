// src/components/statechart/edges.tsx
import React from "react";
import { BaseEdge, EdgeProps, getSmoothStepPath } from "reactflow";

type TransitionEdgeData = {
  /** Mark edge as an initial transition (render dashed). */
  isInitial?: boolean;
  /** Highlight edge when its source is active/next. */
  uiActive?: boolean;
};

export const TransitionEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  data,
}: EdgeProps<TransitionEdgeData>) => {
  const [edgePath] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY });

  const isActive = Boolean(data?.uiActive);
  const isInitial = Boolean(data?.isInitial);

  const style: React.CSSProperties = {
    strokeWidth: isActive ? 2.5 : 2,
    stroke: "hsl(var(--foreground))",
    opacity: isActive ? 0.95 : 0.7,
    // use the variable so linter doesn't complain, and give initial edges a dashed look
    ...(isInitial ? { strokeDasharray: "6 4", opacity: 0.65 } : null),
  };

  return <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />;
};
