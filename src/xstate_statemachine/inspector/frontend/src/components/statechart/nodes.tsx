// statechart/nodes.tsx
import { Handle, NodeProps, Position } from "reactflow";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { RadioTower, Zap } from "lucide-react";

const asArray = (v: any) => (v ? (Array.isArray(v) ? v : [v]) : []);

const Section = ({
  title,
  items,
  icon: Icon,
  colorClass,
}: {
  title: string;
  items: any[];
  icon: any;
  colorClass: string;
}) => {
  if (!items?.length) return null;
  return (
    <div className="mb-2 last:mb-0">
      <h4 className="text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase">
        {title}
      </h4>
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-2 text-[12px] leading-5">
          <Icon className={cn("w-3.5 h-3.5 shrink-0", colorClass)} />
          <span className="truncate">{item.type ?? item.src ?? item}</span>
        </div>
      ))}
    </div>
  );
};

// Simple / Atomic state
export const StateNode = ({ data, selected }: NodeProps) => {
  const entryActions = asArray(data.definition?.entry);
  const invokeServices = asArray(data.definition?.invoke);
  const hasDetails = entryActions.length > 0 || invokeServices.length > 0;
  const isFinal = data.definition?.type === "final";

  const uiStatus = data.uiStatus as undefined | "active" | "next";

  return (
    <Card
      className={cn(
        "w-[240px] rounded-lg border shadow-sm",
        // Active: do NOT fill entire card; keep default bg, maybe a subtle border
        uiStatus === "active" && "bg-card border-blue-500",
        // Next: emphasize with outer ring and primary border
        uiStatus === "next" && "bg-card border-blue-500 ring-2 ring-blue-500/80",
        !uiStatus && "bg-card/90 border-border",
        selected &&
          uiStatus !== "next" &&
          "ring-2 ring-primary/50 ring-offset-2 ring-offset-background",
      )}
    >
      {/* Accept incoming connections */}
      <Handle type="target" position={Position.Top} className="!bg-transparent opacity-0" />

      {/* Header area: only header changes color when active */}
      <CardHeader
        className={cn(
          "p-2.5 rounded-t-lg border-b",
          uiStatus === "active" ? "bg-blue-500 dark:bg-blue-600 text-white" : "bg-muted",
        )}
      >
        <CardTitle className="text-[13px] font-semibold tracking-wide">{data.label}</CardTitle>
      </CardHeader>

      {hasDetails && (
        <CardContent className="p-3">
          <Section title="Entry" items={entryActions} icon={Zap} colorClass="text-yellow-500" />
          <Section
            title="Invoke"
            items={invokeServices}
            icon={RadioTower}
            colorClass="text-blue-500"
          />
        </CardContent>
      )}

      {/* Only show outgoing handles if not a final (end) state */}
      {!isFinal && (
        <>
          <Handle type="source" position={Position.Bottom} className="!bg-transparent opacity-0" />
          <Handle type="source" position={Position.Left} className="!bg-transparent opacity-0" />
          <Handle type="source" position={Position.Right} className="!bg-transparent opacity-0" />
        </>
      )}
    </Card>
  );
};

// Compound state container
export const CompoundStateNode = (props: NodeProps) => (
  <div
    className={cn(
      "rounded-lg border-2 bg-secondary/20",
      props.selected ? "border-primary/60" : "border-border",
    )}
  >
    <div className="p-2 text-[12px] font-bold text-muted-foreground cursor-move border-b bg-secondary/30 rounded-t-lg">
      {props.data.label}
    </div>
    {/* children are rendered by layout; this component is the frame */}
  </div>
);

// Root state summary wrapper
export const RootNode = ({ data, selected }: NodeProps) => {
  const ctxEntries = Object.entries(data.context ?? {}).map(([k, v]) => ({
    key: k,
    type: typeof v,
  }));

  return (
    <Card
      className={cn(
        // Thick border; softer in light, stronger in dark
        "w-full h-full flex flex-col rounded-xl bg-transparent pointer-events-none border-[8px] border-neutral-300/60 dark:border-neutral-600/80",
        selected ? "ring-2 ring-primary/50" : "",
      )}
    >
      {/* Header opaque, stronger background, with high-contrast title color */}
      <CardHeader className="root-drag-handle p-3 border-b bg-muted rounded-t-xl cursor-move pointer-events-auto">
        <CardTitle className="text-[15px] font-semibold tracking-wide text-foreground">
          {data.label}
        </CardTitle>
      </CardHeader>
      {ctxEntries.length > 0 && (
        <CardContent className="px-3 py-1 border-b bg-muted pointer-events-none">
          <h4 className="text-[10px] font-semibold text-muted-foreground mb-0.5 tracking-wide uppercase">
            Context
          </h4>
          {ctxEntries.map(({ key, type }) => (
            <div key={key} className="text-[12px] leading-5">
              <span className="font-mono font-medium">{key}</span>: {type}
            </div>
          ))}
        </CardContent>
      )}
      {/* children nodes are rendered by React Flow; this component is the frame */}
    </Card>
  );
};

// Replace initial triangular marker with nothing; we render dot+arrow on the edge itself
export const InitialNode = () => <div className="w-0 h-0" />;
