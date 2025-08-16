// nodes/StateNode.tsx
import { Handle, NodeProps, Position } from "reactflow";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Power, RadioTower, Zap } from "lucide-react";

type XAction = string | { type?: string; src?: string; [k: string]: any };
type XInvoke = string | { src?: string; id?: string; [k: string]: any };

const arr = <T,>(x?: T | T[]) => (!x ? [] : Array.isArray(x) ? x : [x]);

export const StateNode = ({ data, selected }: NodeProps) => {
  const def = data?.definition ?? {};
  const headerOnly = !!data?.headerOnly;

  const entry = arr<XAction>(def.entry);
  const exit = arr<XAction>(def.exit);
  const invoke = arr<XInvoke>(def.invoke);
  const activities = arr<XAction>(def.activities);

  const hasBody =
    !headerOnly &&
    (entry.length > 0 || exit.length > 0 || invoke.length > 0 || activities.length > 0);

  return (
    <Card
      className={`rounded-xl border ${selected ? "ring-2 ring-primary/60" : ""}`}
      // width fixed by layout; height is AUTO so content can grow
      style={{ width: "100%" }}
    >
      <CardHeader className="py-2 px-3 border-b">
        <CardTitle className="text-sm">{data?.label}</CardTitle>
      </CardHeader>

      {hasBody && (
        <CardContent className="py-2 px-3 space-y-3">
          {entry.length > 0 && (
            <section>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                Entry Actions
              </div>
              <div className="space-y-1">
                {entry.map((a, i) => (
                  <div key={`en-${i}`} className="flex items-center gap-2 text-sm">
                    <Zap className="w-3 h-3" />
                    <span>{typeof a === "string" ? a : (a.type ?? a.src ?? "action")}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {invoke.length > 0 && (
            <section>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                Invoke
              </div>
              <div className="space-y-1">
                {invoke.map((s, i) => {
                  const src = typeof s === "string" ? s : (s.src ?? "service");
                  const id = typeof s === "string" ? undefined : s.id;
                  return (
                    <div key={`inv-${i}`} className="flex items-center gap-2 text-sm">
                      <RadioTower className="w-3 h-3" />
                      <span>{src}</span>
                      {id && <span className="text-xs text-muted-foreground">• {id}</span>}
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {exit.length > 0 && (
            <section>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                Exit Actions
              </div>
              <div className="space-y-1">
                {exit.map((a, i) => (
                  <div key={`ex-${i}`} className="flex items-center gap-2 text-sm">
                    <Power className="w-3 h-3" />
                    <span>{typeof a === "string" ? a : (a.type ?? a.src ?? "action")}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {activities.length > 0 && (
            <section>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                Activities
              </div>
              <div className="space-y-1">
                {activities.map((a, i) => (
                  <div key={`act-${i}`} className="flex items-center gap-2 text-sm">
                    <Zap className="w-3 h-3" />
                    <span>{typeof a === "string" ? a : (a.type ?? a.src ?? "activity")}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </CardContent>
      )}

      {/* 4 ports: we route per-edge to nearest side via sourceHandle/targetHandle */}
      <Handle id="l" type="source" position={Position.Left} className="!bg-primary" />
      <Handle id="r" type="source" position={Position.Right} className="!bg-primary" />
      <Handle id="t" type="source" position={Position.Top} className="!bg-primary" />
      <Handle id="b" type="source" position={Position.Bottom} className="!bg-primary" />

      <Handle id="L" type="target" position={Position.Left} className="!bg-primary" />
      <Handle id="R" type="target" position={Position.Right} className="!bg-primary" />
      <Handle id="T" type="target" position={Position.Top} className="!bg-primary" />
      <Handle id="B" type="target" position={Position.Bottom} className="!bg-primary" />
    </Card>
  );
};
