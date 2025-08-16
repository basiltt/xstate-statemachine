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

export const StateNode = ({ data }: NodeProps) => {
  const entryActions = asArray(data.definition?.entry);
  const invokeServices = asArray(data.definition?.invoke);
  const hasDetails = entryActions.length > 0 || invokeServices.length > 0;
  const isFinal = data.definition?.type === "final";
  const uiStatus = data.uiStatus as undefined | "active" | "next";

  return (
    <Card
      className={cn(
        "w-[240px] rounded-lg border-2 shadow-md",
        uiStatus === "active" && "border-blue-500 bg-blue-500/10",
        uiStatus === "next" && "border-blue-400/50",
        isFinal && "border-dashed",
      )}
    >
      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <CardHeader
        className={cn(
          "p-2.5 rounded-t-md",
          uiStatus === "active" ? "bg-blue-500 text-white" : "bg-muted",
        )}
      >
        <CardTitle className="text-[13px] font-semibold tracking-wide">{data.label}</CardTitle>
      </CardHeader>

      {hasDetails && (
        <CardContent className="p-3">
          <Section
            title="Entry actions"
            items={entryActions}
            icon={Zap}
            colorClass="text-yellow-500"
          />
          <Section
            title="Invoke"
            items={invokeServices}
            icon={RadioTower}
            colorClass="text-blue-500"
          />
        </CardContent>
      )}
      {!isFinal && <Handle type="source" position={Position.Bottom} className="!opacity-0" />}
    </Card>
  );
};

export const EventNode = ({ data }: NodeProps) => {
  return (
    <div className="bg-card text-card-foreground rounded-md text-sm font-medium border-2 px-4 py-2 shadow-sm">
      {data.label}
      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </div>
  );
};

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
  </div>
);

export const RootNode = ({ data }: NodeProps) => {
  const ctxEntries = Object.entries(data.context ?? {}).map(([k, v]) => ({
    key: k,
    type: typeof v,
  }));

  return (
    <Card
      className={cn(
        "w-full h-full flex flex-col rounded-xl bg-transparent pointer-events-none border-[6px] border-neutral-300/60 dark:border-neutral-700/80",
      )}
    >
      <CardHeader className="root-drag-handle p-3 border-b bg-muted/80 backdrop-blur-sm rounded-t-lg cursor-move pointer-events-auto">
        <CardTitle className="text-[15px] font-semibold tracking-wide text-foreground">
          {data.label}
        </CardTitle>
      </CardHeader>
      {ctxEntries.length > 0 && (
        <CardContent className="px-3 py-1 border-b bg-muted/80 backdrop-blur-sm pointer-events-none">
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
    </Card>
  );
};

export const InitialNode = () => <div className="w-0 h-0" />;
