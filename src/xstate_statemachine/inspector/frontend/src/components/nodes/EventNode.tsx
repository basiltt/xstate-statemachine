// //  src/xstate_statemachine/inspector/frontend/src/components/nodes/EventNode.tsx

// import { Handle, NodeProps, Position } from "reactflow";

import { NodeProps } from "reactflow";

export const EventNode = ({ data }: NodeProps) => {
  return (
    <div className="px-3 py-1.5 rounded-full border text-[12px] leading-5 bg-background/70 backdrop-blur-sm shadow-sm">
      <span className="font-mono">{data.label}</span>
    </div>
  );
};
