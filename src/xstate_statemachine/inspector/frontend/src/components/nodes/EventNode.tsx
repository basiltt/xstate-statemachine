// nodes/EventNode.tsx
import { Handle, NodeProps, Position } from "reactflow";

export const EventNode = ({ data, selected }: NodeProps) => {
  return (
    <div
      className={[
        "rounded-full border bg-background text-foreground shadow-sm",
        "px-4 py-1 text-sm font-medium",
        selected ? "ring-2 ring-primary/60" : "",
      ].join(" ")}
      style={{ width: "100%" }}
    >
      {data.label}

      <Handle id="l" type="source" position={Position.Left} className="!bg-primary" />
      <Handle id="r" type="source" position={Position.Right} className="!bg-primary" />
      <Handle id="t" type="source" position={Position.Top} className="!bg-primary" />
      <Handle id="b" type="source" position={Position.Bottom} className="!bg-primary" />

      <Handle id="L" type="target" position={Position.Left} className="!bg-primary" />
      <Handle id="R" type="target" position={Position.Right} className="!bg-primary" />
      <Handle id="T" type="target" position={Position.Top} className="!bg-primary" />
      <Handle id="B" type="target" position={Position.Bottom} className="!bg-primary" />
    </div>
  );
};
