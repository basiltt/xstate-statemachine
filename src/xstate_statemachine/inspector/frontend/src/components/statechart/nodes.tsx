// src/xstate_statemachine/inspector/frontend/src/components/statechart/nodes.tsx

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

// Provide a fixed pool of invisible handles around all 4 sides so routing can
// connect anywhere and distribute multiple edges without overlaps. Indexed ids
// are used (e.g. l0..lN, r0..rN for sources; L0..LN, R0..RN for targets).
const PORTS_PER_SIDE = 24; // ample capacity; routing code will only use needed ones

function SideHandles({
  side,
  type,
  upper,
}: {
  side: "top" | "bottom" | "left" | "right";
  type: "source" | "target";
  upper: string; // single-letter id prefix (t/b/l/r or T/B/L/R)
}) {
  const isHorizontal = side === "top" || side === "bottom";
  const position =
    side === "top"
      ? Position.Top
      : side === "bottom"
        ? Position.Bottom
        : side === "left"
          ? Position.Left
          : Position.Right;

  return (
    <>
      {Array.from({ length: PORTS_PER_SIDE }).map((_, i) => {
        const pct = ((i + 1) / (PORTS_PER_SIDE + 1)) * 100;
        const style = isHorizontal
          ? ({ left: `${pct}%` } as React.CSSProperties)
          : ({ top: `${pct}%` } as React.CSSProperties);
        return (
          <Handle
            key={`${upper}${i}`}
            id={`${upper}${i}`}
            type={type}
            position={position}
            className="!opacity-0"
            style={style}
          />
        );
      })}
    </>
  );
}

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
      {/* Targets on all sides (uppercase ids) */}
      <SideHandles side="top" type="target" upper="T" />
      <SideHandles side="bottom" type="target" upper="B" />
      <SideHandles side="left" type="target" upper="L" />
      <SideHandles side="right" type="target" upper="R" />
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
      {/* Sources on all sides (lowercase ids). Final states emit no outgoing transitions. */}
      {!isFinal && (
        <>
          <SideHandles side="top" type="source" upper="t" />
          <SideHandles side="bottom" type="source" upper="b" />
          <SideHandles side="left" type="source" upper="l" />
          <SideHandles side="right" type="source" upper="r" />
        </>
      )}
    </Card>
  );
};

export const EventNode = ({ data }: NodeProps) => {
  return (
    <div className="bg-card text-card-foreground rounded-md text-sm font-medium border-2 px-4 py-2 shadow-sm">
      {data.label}
      {/* Targets and sources on all sides for events too */}
      <SideHandles side="top" type="target" upper="T" />
      <SideHandles side="bottom" type="target" upper="B" />
      <SideHandles side="left" type="target" upper="L" />
      <SideHandles side="right" type="target" upper="R" />
      <SideHandles side="top" type="source" upper="t" />
      <SideHandles side="bottom" type="source" upper="b" />
      <SideHandles side="left" type="source" upper="l" />
      <SideHandles side="right" type="source" upper="r" />
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
