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
    borderRadius: 12,
    offset: 20,
  });

  // Calculate offset position to avoid node overlaps
  const deltaX = targetX - sourceX;
  const deltaY = targetY - sourceY;
  const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  
  // Position label closer to source node with offset to avoid overlaps
  const offsetRatio = 0.3; // Position at 30% along the edge
  const offsetDistance = 25; // Minimum distance from edge path
  
  let adjustedLabelX = labelX;
  let adjustedLabelY = labelY;
  
  if (distance > 0) {
    // Calculate perpendicular offset to move label away from potential node overlaps
    const perpX = -deltaY / distance;
    const perpY = deltaX / distance;
    
    // Move label along the edge (closer to source) and offset perpendicular
    adjustedLabelX = sourceX + deltaX * offsetRatio + perpX * offsetDistance;
    adjustedLabelY = sourceY + deltaY * offsetRatio + perpY * offsetDistance;
  }

  const actions = asArray(data?.actions);
  const isInitial = Boolean((data as any)?.isInitial) || id.includes(".__initial__");

  // small curved arrow segment from the source, plus a big dot at the start
  const dx =
    Math.max(16, Math.min(28, Math.abs(targetX - sourceX) * 0.2)) *
    Math.sign(targetX - sourceX || 1);
  const dy = (targetY - sourceY) * 0.15;
  const shortPath = `M ${sourceX} ${sourceY} Q ${sourceX + dx * 0.5} ${sourceY + dy * 0.6}, ${sourceX + dx} ${sourceY + dy}`;

  return (
    <>
      {isInitial && (
        <g>
          <circle
            cx={sourceX - 8 * Math.sign(targetX - sourceX || 1)}
            cy={sourceY}
            r={6}
            style={{
              // solid foreground dot with a subtle outline for contrast in both themes
              fill: "hsl(var(--foreground))",
              stroke: "hsl(var(--background))",
              strokeWidth: 2,
            }}
          />
          <path
            d={shortPath}
            style={{ stroke: "hsl(var(--foreground))", strokeWidth: 1.75, fill: "none" }}
          />
        </g>
      )}

      <BaseEdge 
        id={id} 
        path={edgePath} 
        markerEnd={markerEnd} 
        style={{ 
          strokeWidth: 2, 
          stroke: "hsl(var(--foreground))",
          strokeDasharray: data?.guard ? "5,5" : "none"
        }} 
      />
      <EdgeLabelRenderer>
        <div
          style={{ 
            transform: `translate(-50%, -50%) translate(${adjustedLabelX}px, ${adjustedLabelY}px)`,
            pointerEvents: 'all'
          }}
          className="absolute rounded-full border bg-background/95 px-2.5 py-0.5 text-xs font-medium shadow cursor-move hover:bg-background hover:shadow-md transition-all"
          onMouseDown={(e) => {
            e.stopPropagation();
          }}
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
