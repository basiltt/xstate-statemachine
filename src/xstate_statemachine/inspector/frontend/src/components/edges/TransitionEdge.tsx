import { EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from "reactflow";
import { cn } from "@/lib/utils";

export const TransitionEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path stroke-2 stroke-primary/50"
        d={edgePath}
        markerEnd={markerEnd}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className="nodrag nopan"
        >
          <div
            className={cn(
              "px-2 py-0.5 rounded-full text-xs font-medium",
              "bg-background text-foreground border shadow-sm",
            )}
          >
            {data.label}
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  );
};
