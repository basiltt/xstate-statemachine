import { NodeProps } from "reactflow";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const RootNode = ({ data }: NodeProps) => {
  const ctx = data?.context ?? {};
  const entries = Object.keys(ctx).map((k) => ({ key: k, type: String(ctx[k] ?? "any") }));

  return (
    <Card className="w-full h-full rounded-2xl overflow-hidden border-2">
      <CardHeader className="py-2 px-4 border-b">
        <CardTitle className="text-base">{data?.label ?? "StateMachine"}</CardTitle>
      </CardHeader>
      {entries.length > 0 && (
        <CardContent className="py-2 px-4 border-b">
          <h4 className="text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase">
            Context
          </h4>
          <div className="space-y-1">
            {entries.map(({ key, type }) => (
              <div key={key} className="text-[12px] leading-5">
                <span className="font-mono font-medium">{key}</span>: {type}
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
};
