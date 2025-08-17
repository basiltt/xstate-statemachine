//  src/xstate_statemachine/inspector/frontend/src/components/nodes/StateNode.tsx

import { Handle, NodeProps, Position } from "reactflow";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioTower, Zap } from "lucide-react";
import { cn } from "@/lib/utils.ts";

export const StateNode = ({ data }: NodeProps) => {
  const entryActions = Array.isArray(data.definition?.entry)
    ? data.definition.entry
    : data.definition?.entry
      ? [data.definition.entry]
      : [];
  const invokeServices = Array.isArray(data.definition?.invoke)
    ? data.definition.invoke
    : data.definition?.invoke
      ? [data.definition.invoke]
      : [];
  const hasDetails = entryActions.length > 0 || invokeServices.length > 0;
  const isFinal = data.definition?.type === "final";
  const uiStatus = data.uiStatus as undefined | "active" | "next";

  return (
    <Card
      className={cn(
        "w-[240px] rounded-xl border-2",
        "bg-card/70 backdrop-blur-sm",
        "shadow-sm",
        isFinal && "border-dashed",
        uiStatus === "active" && "border-blue-500 ring-2 ring-blue-500/20",
        uiStatus === "next" && "border-blue-400/70 ring-1 ring-blue-400/20",
      )}
    >
      <Handle type="target" position={Position.Top} className="!opacity-0" />

      <CardHeader
        className={cn(
          "p-2.5 rounded-t-xl border-b",
          uiStatus === "active"
            ? "bg-blue-500 text-white border-blue-500"
            : "bg-muted/60 border-border/40",
        )}
      >
        <CardTitle className="text-[13px] font-semibold tracking-wide truncate">
          {data.label}
        </CardTitle>
      </CardHeader>

      {hasDetails && (
        <CardContent className="p-3">
          {entryActions.length > 0 && (
            <div className="mb-2">
              <h4 className="text-[10px] font-semibold text-muted-foreground mb-1 uppercase tracking-wide">
                Entry actions
              </h4>
              {entryActions.map((a: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-[12px] leading-5">
                  <Zap className="w-3.5 h-3.5 text-yellow-500" />
                  <span className="truncate">{a?.type ?? a}</span>
                </div>
              ))}
            </div>
          )}
          {invokeServices.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-muted-foreground mb-1 uppercase tracking-wide">
                Invoke
              </h4>
              {invokeServices.map((svc: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-[12px] leading-5">
                  <RadioTower className="w-3.5 h-3.5 text-blue-500" />
                  <span className="truncate">{svc?.src ?? svc}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      )}

      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </Card>
  );
};
