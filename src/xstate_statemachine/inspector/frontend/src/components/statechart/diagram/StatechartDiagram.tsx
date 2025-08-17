// src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/StatechartDiagram.tsx

import { useCallback, useRef, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, ReactFlowProvider } from "reactflow";
import "reactflow/dist/style.css";

import { MachineState } from "@/hooks/useInspectorSocket.ts";
import { useDiagram } from "@/components/statechart/diagram/hooks/useDiagram.ts";
import { DiagramContextMenu } from "@/components/statechart/diagram/DiagramContextMenu.tsx";
import reactFlowConfig from "@/components/statechart/diagram/diagramConfig";

type DiagramProps = {
  machine: MachineState;
  activeStateIds: string[];
  autoFitAfterDrag?: boolean;
  showMinimap?: boolean;
};

const DiagramCanvas = ({
  machine,
  activeStateIds,
  autoFitAfterDrag = true,
  showMinimap = true,
}: DiagramProps) => {
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
    hasSavedPositions,
    onMoveEnd,
    initialViewport,
  } = useDiagram({ machine, activeStateIds, autoFitAfterDrag });

  const onPaneContextMenu = useCallback((evt: React.MouseEvent) => {
    evt.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    setMenu({ open: true, x: evt.clientX - (rect?.left ?? 0), y: evt.clientY - (rect?.top ?? 0) });
  }, []);

  const closeMenu = useCallback(() => setMenu((m) => ({ ...m, open: false })), []);

  const handleAutoLayout = () => relayout({ resetSavedPositions: true }).catch(console.error);
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
        onMoveEnd={onMoveEnd}
        // Spread in all the static config
        {...reactFlowConfig}
        // Specific props
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        defaultViewport={initialViewport ?? undefined}
        fitView={!hasSavedPositions && !initialViewport}
        minZoom={0.2}
        maxZoom={1.5}
        snapToGrid
        className="bg-background"
      >
        <Controls />
        {showMinimap && (
          <MiniMap
            className="rounded-md border shadow-sm"
            style={{ backgroundColor: "hsl(var(--card))" }}
            maskColor={"hsl(var(--background) / 0.6)"}
            nodeColor={() => "hsl(var(--muted))"}
            nodeStrokeColor={() => "hsl(var(--border))"}
          />
        )}
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
