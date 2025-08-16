import { Handle, NodeProps, Position } from "reactflow";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowRight, RadioTower, Zap } from "lucide-react";

export const StateNode = ({ data, selected }: NodeProps) => {
  const isCompound = data.definition.states;

  // FIX: Normalize 'entry' and 'invoke' to always be arrays
  const entryActions = data.definition.entry
    ? Array.isArray(data.definition.entry)
      ? data.definition.entry
      : [data.definition.entry]
    : [];

  const invokeServices = data.definition.invoke
    ? Array.isArray(data.definition.invoke)
      ? data.definition.invoke
      : [data.definition.invoke]
    : [];

  const hasDetails = entryActions.length > 0 || invokeServices.length > 0;

  return (
    <Card
      className={cn(
        "bg-card text-card-foreground shadow-lg border-2 w-[220px]", // Enforce a fixed width
        selected ? "border-primary" : "border-border",
        isCompound ? "bg-secondary/30 dark:bg-secondary/20" : "bg-card",
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-primary" />
      <CardHeader className="p-3">
        <CardTitle className="text-base flex items-center gap-2">
          {data.definition.initial && <ArrowRight className="w-4 h-4 text-muted-foreground" />}
          {data.label}
        </CardTitle>
      </CardHeader>

      {hasDetails && (
        <CardContent className="p-3 border-t">
          {entryActions.length > 0 && (
            <div className="mb-2">
              <h4 className="text-xs font-bold text-muted-foreground mb-1">Entry Actions</h4>
              {/* FIX: Map over the normalized array */}
              {entryActions.map((action: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <Zap className="w-3 h-3 text-yellow-500" />
                  <span>{action.type || action}</span>
                </div>
              ))}
            </div>
          )}
          {invokeServices.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-muted-foreground mb-1">Invoke</h4>
              {/* FIX: Map over the normalized array */}
              {invokeServices.map((service: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <RadioTower className="w-3 h-3 text-blue-500" />
                  <span>{service.src}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </Card>
  );
};
