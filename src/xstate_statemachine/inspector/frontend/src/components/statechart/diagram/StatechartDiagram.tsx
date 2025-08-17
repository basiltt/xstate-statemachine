// src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/StatechartDiagram.tsx

import { useCallback, useRef, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, ReactFlowProvider } from "reactflow";
import "reactflow/dist/style.css";

import { MachineState } from "@/hooks/useInspectorSocket.ts";
import { useDiagram } from "@/components/statechart/diagram/useDiagram.ts";
import { DiagramContextMenu } from "@/components/statechart/diagram/DiagramContextMenu.tsx";
import * as diagramConfig from "@/components/statechart/diagram/diagramConfig.ts";

type DiagramProps = {
  machine: MachineState;
  activeStateIds: string[];
};

const DiagramCanvas = ({ machine, activeStateIds }: DiagramProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState<{ open: boolean; x: number; y: number }>({
    open: false,
    x: 0,
    y: 0,
  });

  // All complex logic is now neatly contained in this hook
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onNodeDragStop,
    relayout,
    tightenAndFitWhenReady,
  } = useDiagram({ machine, activeStateIds });

  const onPaneContextMenu = useCallback((evt: React.MouseEvent) => {
    evt.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    setMenu({ open: true, x: evt.clientX - (rect?.left ?? 0), y: evt.clientY - (rect?.top ?? 0) });
  }, []);

  const closeMenu = useCallback(() => setMenu((m) => ({ ...m, open: false })), []);

  const handleAutoLayout = () => relayout().catch(console.error);
  const handleFitView = () => tightenAndFitWhenReady(edges).catch(console.error);

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
        onPaneContextMenu={onPaneContextMenu}
        // Spread in all the static config
        {...diagramConfig}
        // Specific props
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        snapToGrid
        className="bg-background"
      >
        <Controls />
        <MiniMap />
        <Background />
      </ReactFlow>

      {menu.open && (
        <DiagramContextMenu
          x={menu.x}
          y={menu.y}
          onClose={closeMenu}
          onAutoLayout={handleAutoLayout}
          onFitView={handleFitView}
        />
      )}
    </div>
  );
};

// The provider wrapper remains the same
export const StatechartDiagram = (props: DiagramProps) => (
  <ReactFlowProvider>
    <DiagramCanvas {...props} />
  </ReactFlowProvider>
);
