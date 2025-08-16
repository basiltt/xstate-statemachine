// StatechartDiagram.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  ConnectionLineType,
  Controls,
  type EdgeChange,
  MarkerType,
  MiniMap,
  type Node,
  type NodeChange,
  ReactFlowProvider,
  SelectionMode,
  useReactFlow,
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

const PADDING = 40; // wrapper padding around children

const DiagramCanvas = ({ machine, activeStateIds }: DiagramProps) => {
  const initialLayout = useMemo(
    () => getLayoutedElements(machine.definition, machine.context),
    [machine.definition, machine.context],
  );

  // 👉 Controlled state
  const [nodes, setNodes] = useState(() =>
    initialLayout.nodes.map((n: any) => ({
      ...n,
      // whole node draggable
      selected: activeStateIds.includes(n.id),
    })),
  );
  const [edges, setEdges] = useState(initialLayout.edges);

  // @ts-ignore
  const { fitView, getNodes, updateNodeInternals } = useReactFlow();

  // Utility: compute tight wrapper bounds for the root node from current nodes
  const computeRootBounds = useCallback((allNodes: Node[]) => {
    const root = allNodes.find((n) => n.type === "rootNode");
    if (!root) return null;
    const children = allNodes.filter((n) => n.parentNode === root.id);
    if (children.length === 0) return null;

    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;

    for (const ch of children) {
      const w = (ch as any).width ?? 250;
      const h = (ch as any).height ?? 60;
      minX = Math.min(minX, ch.position.x);
      minY = Math.min(minY, ch.position.y);
      maxX = Math.max(maxX, ch.position.x + w);
      maxY = Math.max(maxY, ch.position.y + h);
    }

    const width = Math.max(maxX - minX + PADDING, 200);
    const height = Math.max(maxY - minY + PADDING, 140);

    return { minX, minY, maxX, maxY, width, height };
  }, []);

  // Expand-only wrapper during drag if children approach edges
  const maybeGrowRootDuringDrag = useCallback(
    (currentNodes: Node[]) => {
      const rootIndex = currentNodes.findIndex((n) => n.type === "rootNode");
      if (rootIndex < 0) return currentNodes;
      const root = currentNodes[rootIndex];

      const tight = computeRootBounds(currentNodes);
      if (!tight) return currentNodes;

      const currWidth = (root.style as any)?.width ?? (root as any).width ?? tight.width;
      const currHeight = (root.style as any)?.height ?? (root as any).height ?? tight.height;

      const needLeftPad = tight.minX < PADDING / 2;
      const needTopPad = tight.minY < PADDING / 2;
      const dx = needLeftPad ? tight.minX - PADDING / 2 : 0;
      const dy = needTopPad ? tight.minY - PADDING / 2 : 0;

      const nextWidth = Math.max(currWidth, tight.width);
      const nextHeight = Math.max(currHeight, tight.height);

      if (!needLeftPad && !needTopPad && nextWidth === currWidth && nextHeight === currHeight) {
        return currentNodes; // no-op
      }

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          return {
            ...n,
            position: { x: n.position.x + dx, y: n.position.y + dy },
            style: { ...(n.style as any), width: nextWidth, height: nextHeight },
          } as Node;
        }
        if (n.parentNode === root.id) {
          // Keep world position stable while root moves
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } } as Node;
        }
        return n;
      });

      if (typeof updateNodeInternals === "function") {
        updateNodeInternals(root.id);
      }
      return updated;
    },
    [computeRootBounds, updateNodeInternals],
  );

  // Tight fit wrapper after drag stop or structural updates.
  // Reposition root so there is PADDING/2 on the top/left of the closest child,
  // and offset children so their world positions stay the same.
  const fitRootTightly = useCallback(
    (currentNodes: Node[]) => {
      const rootIndex = currentNodes.findIndex((n) => n.type === "rootNode");
      if (rootIndex < 0) return currentNodes;
      const root = currentNodes[rootIndex];

      const tight = computeRootBounds(currentNodes);
      if (!tight) return currentNodes;

      const dx = tight.minX - PADDING / 2;
      const dy = tight.minY - PADDING / 2;

      const newRoot = {
        ...root,
        position: { x: root.position.x + dx, y: root.position.y + dy },
        style: { ...(root.style as any), width: tight.width, height: tight.height },
      } as Node;

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) return newRoot;
        if (n.parentNode === root.id) {
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } } as Node;
        }
        return n;
      });

      if (typeof updateNodeInternals === "function") {
        updateNodeInternals(root.id);
      }
      return updated;
    },
    [computeRootBounds, updateNodeInternals],
  );

  // Reset positions & selections if the machine changes
  useEffect(() => {
    setNodes(
      initialLayout.nodes.map((n: any) => ({
        ...n,
        selected: activeStateIds.includes(n.id),
      })),
    );
    setEdges(initialLayout.edges);
    const id = setTimeout(() => {
      // After initial render, tightly fit wrapper once more (sizes may change after measure)
      setNodes((prev) => fitRootTightly(prev));
      fitView({ duration: 400, padding: 0.1 });
    }, 50);
    return () => clearTimeout(id);
  }, [initialLayout, activeStateIds, fitRootTightly, fitView]);

  // Keep selection highlighting in sync
  useEffect(() => {
    setNodes((prev) => prev.map((n) => ({ ...n, selected: activeStateIds.includes(n.id) })));
  }, [activeStateIds]);

  // Controlled handlers
  const onNodesChange = useCallback(
    (changes: NodeChange[]) =>
      setNodes((nds) => {
        const next = applyNodeChanges(changes, nds);
        // whenever nodes change (positions, dimensions), keep wrapper tight
        return fitRootTightly(next);
      }),
    [fitRootTightly],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  const onNodeDrag = useCallback(() => {
    // Grow-only during drag for smoother UX
    setNodes((prev) => maybeGrowRootDuringDrag(prev));
  }, [maybeGrowRootDuringDrag]);

  const onNodeDragStop = useCallback(() => {
    // Tight fit after drag ends
    setNodes((prev) => fitRootTightly(prev));
  }, [fitRootTightly]);

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
      onNodeDrag={onNodeDrag}
      onNodeDragStop={onNodeDragStop}
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
      className="bg-background"
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
