// statechart/edges.tsx
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from "reactflow";
import { Zap } from "lucide-react";

const asArray = (v: any) => (v ? (Array.isArray(v) ? v : [v]) : []);

export const TransitionEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  data,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    borderRadius: 16,
  });

  const actions = asArray(data?.actions);

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={{ strokeWidth: 1.5 }} />
      <EdgeLabelRenderer>
        <div
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          className="nodrag nopan absolute rounded-full border bg-background/95 px-2.5 py-0.5 text-xs font-medium shadow"
        >
          <div className="text-center">{data?.label}</div>
          {actions.length > 0 && <hr className="my-1" />}
          {actions.map((action: any, i: number) => (
            <div key={i} className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Zap className="w-3 h-3 text-yellow-500" />
              <span>{action.type ?? action}</span>
            </div>
          ))}
        </div>
      </EdgeLabelRenderer>
    </>
  );
};
