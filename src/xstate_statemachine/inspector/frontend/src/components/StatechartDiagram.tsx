// StatechartDiagram.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  ConnectionLineType,
  MarkerType,
  SelectionMode,
  useReactFlow,
  type EdgeChange,
  type NodeChange,
} from "reactflow";
import "reactflow/dist/style.css";

import { MachineState } from "@/hooks/useInspectorSocket";
import { getLayoutedElements } from "./statechart/layout";
import { CompoundStateNode, InitialNode, RootNode, StateNode } from "./statechart/nodes";
import { TransitionEdge } from "./statechart/edges";

const nodeTypes = {
  rootNode: RootNode,
  stateNode: StateNode,
  compoundStateNode: CompoundStateNode,
  initialNode: InitialNode,
};
const edgeTypes = { transitionEdge: TransitionEdge };

interface DiagramProps {
  machine: MachineState;
  activeStateIds: string[];
}

const DiagramCanvas = ({ machine, activeStateIds }: DiagramProps) => {
  const initialLayout = useMemo(
    () => getLayoutedElements(machine.definition),
    // Re-layout only when the definition actually changes (e.g., different machine)
    [machine.definition],
  );

  // 👉 Controlled state
  const [nodes, setNodes] = useState(() =>
    initialLayout.nodes.map((n: any) => ({
      ...n,
      dragHandle: ".drag-handle",
      selected: activeStateIds.includes(n.id),
    })),
  );
  const [edges, setEdges] = useState(initialLayout.edges);

  const { fitView } = useReactFlow();

  // Reset positions & selections if the machine changes
  useEffect(() => {
    setNodes(
      initialLayout.nodes.map((n: any) => ({
        ...n,
        dragHandle: ".drag-handle",
        selected: activeStateIds.includes(n.id),
      })),
    );
    setEdges(initialLayout.edges);
    // small delay so measurements are ready before fitting
    const id = setTimeout(() => fitView({ duration: 400, padding: 0.1 }), 50);
    return () => clearTimeout(id);
  }, [initialLayout, activeStateIds, fitView]);

  // Keep selection highlighting in sync
  useEffect(() => {
    setNodes((prev) => prev.map((n) => ({ ...n, selected: activeStateIds.includes(n.id) })));
  }, [activeStateIds]);

  // Controlled handlers
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      proOptions={{ hideAttribution: true }}
      // Interaction: match XState editor feel
      nodesDraggable
      nodesConnectable={false}
      elementsSelectable
      selectionOnDrag
      panOnDrag={false}
      selectionMode={SelectionMode.Partial}
      connectionLineType={ConnectionLineType.SmoothStep}
      defaultEdgeOptions={{
        type: "transitionEdge",
        markerEnd: { type: MarkerType.ArrowClosed },
      }}
      // Zoom & background similar to XState
      fitView
      minZoom={0.2}
      maxZoom={1.5}
      className="bg-muted/40"
    >
      <Controls />
      <MiniMap
        nodeColor={(n) => (n.selected ? "hsl(var(--primary))" : "hsl(var(--border))")}
        nodeStrokeWidth={3}
      />
      <Background />
    </ReactFlow>
  );
};

export const StatechartDiagram = (props: DiagramProps) => (
  <ReactFlowProvider>
    <DiagramCanvas {...props} />
  </ReactFlowProvider>
);
