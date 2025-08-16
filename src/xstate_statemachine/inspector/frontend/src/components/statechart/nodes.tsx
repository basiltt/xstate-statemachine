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

  return (
    // Entire card is draggable by default (no dragHandle restriction)
    <Card
      className={cn(
        "w-[240px] rounded-lg border shadow-sm bg-card/90",
        selected ? "ring-2 ring-primary ring-offset-2 ring-offset-background" : "border-border",
      )}
    >
      {/* Accept incoming connections */}
      <Handle type="target" position={Position.Top} className="!bg-transparent opacity-0" />

      {/* Header area */}
      <CardHeader className="p-2.5 cursor-move bg-muted/60 rounded-t-lg border-b">
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
        "w-full h-full flex flex-col rounded-xl border-2 bg-card/70",
        selected ? "border-primary/60" : "border-border",
      )}
    >
      <CardHeader className="p-3 border-b bg-muted/40 rounded-t-xl cursor-move">
        <CardTitle className="text-sm">{data.label}</CardTitle>
      </CardHeader>
      {ctxEntries.length > 0 && (
        <CardContent className="p-3">
          <h4 className="text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase">
            Context
          </h4>
          {ctxEntries.map(({ key, type }) => (
            <div key={key} className="text-[12px] leading-5">
              <span className="font-mono font-medium">{key}</span>: {type}
            </div>
          ))}
        </CardContent>
      )}
      {/* children nodes are rendered on top by React Flow; this component is just the frame */}
    </Card>
  );
};

export const InitialNode = () => (
  <div className="w-0 h-0 border-t-4 border-b-4 border-l-8 border-t-transparent border-b-transparent border-l-foreground" />
);
