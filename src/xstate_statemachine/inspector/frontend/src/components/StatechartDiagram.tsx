// StatechartDiagram.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  ConnectionLineType,
  Controls,
  type Edge,
  type EdgeChange,
  MarkerType,
  MiniMap,
  type Node,
  type NodeChange,
  ReactFlowProvider,
  useReactFlow,
  useUpdateNodeInternals,
} from "reactflow";
import "reactflow/dist/style.css";

import { MachineState } from "@/hooks/useInspectorSocket";
import { getLayoutedElements } from "./statechart/layout";
import { EDGE_CLEAR_TOP, estimateReservedTop, PADDING, ROOT_HEADER } from "./statechart/constants";
import { CompoundStateNode, EventNode, InitialNode, RootNode, StateNode } from "./statechart/nodes";
import { TransitionEdge } from "./statechart/edges";

const nodeTypes = {
  rootNode: RootNode,
  stateNode: StateNode,
  compoundStateNode: CompoundStateNode,
  initialNode: InitialNode,
  eventNode: EventNode,
};
const edgeTypes = { transitionEdge: TransitionEdge };

interface DiagramProps {
  machine: MachineState;
  activeStateIds: string[];
}

const EDGE_MARGIN = 48;

const DiagramCanvas = ({ machine, activeStateIds }: DiagramProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [menu, setMenu] = useState<{ open: boolean; x: number; y: number }>({
    open: false,
    x: 0,
    y: 0,
  });

  const { fitView } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const reservedTop = useMemo(
    () => estimateReservedTop(machine.context) + EDGE_CLEAR_TOP,
    [machine.context],
  );

  /**
   * Restored: Decorates nodes with 'active' or 'next' status for highlighting.
   */
  const decorateStatuses = useCallback(
    (list: Node[], eds: Edge[]): Node[] => {
      const activeSet = new Set(activeStateIds);
      const nextSet = new Set<string>();
      for (const e of eds) {
        if (activeSet.has(e.source)) {
          const nextEdge = eds.find((edge) => edge.source === e.target);
          if (nextEdge) {
            nextSet.add(nextEdge.target);
          }
        }
      }
      return list.map((n) => {
        const uiStatus = activeSet.has(n.id) ? "active" : nextSet.has(n.id) ? "next" : undefined;
        return { ...n, data: { ...n.data, uiStatus } };
      });
    },
    [activeStateIds],
  );

  /**
   * Calculates the tightest possible bounding box around all child nodes.
   */
  const computeRootBounds = useCallback(
    (allNodes: Node[], eds: Edge[]) => {
      const root = allNodes.find((n) => n.type === "rootNode");
      if (!root) return null;
      const children = allNodes.filter((n) => n.parentId === root.id);
      if (children.length === 0) return null;

      let minX = Infinity,
        minY = Infinity,
        maxX = -Infinity,
        maxY = -Infinity;

      for (const ch of children) {
        minX = Math.min(minX, ch.position.x);
        minY = Math.min(minY, ch.position.y);
        maxX = Math.max(maxX, ch.position.x + (ch.width || 0));
        maxY = Math.max(maxY, ch.position.y + (ch.height || 0));
      }

      // Include edges in bounds calculation for better padding
      const idToNode = new Map(allNodes.map((n) => [n.id, n] as const));
      for (const e of eds) {
        const s = idToNode.get(e.source);
        const t = idToNode.get(e.target);
        if (!s || !t || s.parentId !== root.id || t.parentId !== root.id) continue;

        const sx = s.position.x + (s.width || 0) / 2;
        const sy = s.position.y + (s.height || 0) / 2;
        const tx = t.position.x + (t.width || 0) / 2;
        const ty = t.position.y + (t.height || 0) / 2;

        minX = Math.min(minX, Math.min(sx, tx) - EDGE_MARGIN);
        maxX = Math.max(maxX, Math.max(sx, tx) + EDGE_MARGIN);
        minY = Math.min(minY, Math.min(sy, ty) - EDGE_MARGIN);
        maxY = Math.max(maxY, Math.max(sy, ty) + EDGE_MARGIN);
      }

      const width = Math.max(maxX - minX + PADDING, 200);
      const height = Math.max(maxY - minY + PADDING + reservedTop - ROOT_HEADER, 140 + reservedTop);

      return { minX, minY, width, height };
    },
    [reservedTop],
  );

  /**
   * Restored: Smooth "grow-only" resizing for the best UX during a drag operation.
   */
  const maybeGrowRootDuringDrag = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const rootNode = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!rootNode || !tight) return currentNodes;

      const currWidth = rootNode.width || tight.width;
      const currHeight = rootNode.height || tight.height;

      const nextWidth = Math.max(currWidth, tight.width);
      const nextHeight = Math.max(currHeight, tight.height);

      if (nextWidth === currWidth && nextHeight === currHeight) return currentNodes;

      const updatedNodes = currentNodes.map((n) => {
        if (n.id === rootNode.id) {
          return { ...n, style: { ...n.style, width: nextWidth, height: nextHeight } };
        }
        return n;
      });
      updateNodeInternals(rootNode.id);
      return updatedNodes;
    },
    [computeRootBounds, updateNodeInternals],
  );

  /**
   * Restored: A robust function to snap the wrapper to the perfect size.
   * Used for initial layout and after a drag is complete.
   */
  const fitRootTightly = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const rootNode = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!rootNode || !tight) return currentNodes;

      const dx = tight.minX - PADDING / 2;
      const dy = tight.minY - PADDING / 2;

      const updatedNodes = currentNodes.map((n) => {
        if (n.id === rootNode.id) {
          return {
            ...n,
            position: { x: rootNode.position.x + dx, y: rootNode.position.y + dy },
            style: { ...n.style, width: tight.width, height: tight.height },
          };
        }
        if (n.parentId === rootNode.id) {
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } };
        }
        return n;
      });
      updateNodeInternals(rootNode.id);
      return updatedNodes;
    },
    [computeRootBounds, updateNodeInternals],
  );

  const relayout = useCallback(async () => {
    const { nodes: newNodes, edges: newEdges } = await getLayoutedElements(
      machine.definition,
      machine.context,
    );
    setEdges(newEdges);
    setNodes(fitRootTightly(decorateStatuses(newNodes, newEdges), newEdges));
    setTimeout(() => fitView({ duration: 400, padding: 0.1 }), 100);
  }, [machine.definition, machine.context, decorateStatuses, fitRootTightly, fitView]);

  useEffect(() => {
    relayout().catch(console.error);
  }, [relayout]);

  useEffect(() => {
    setNodes((prev) => decorateStatuses(prev, edges));
  }, [activeStateIds, edges, decorateStatuses]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((currentNodes) => {
        const nextNodes = applyNodeChanges(changes, currentNodes);
        const isDrag = changes.some((c) => c.type === "position" && c.dragging);

        if (isDrag) {
          // Use the smooth "grow-only" function during the drag
          return maybeGrowRootDuringDrag(nextNodes, edges);
        }

        return decorateStatuses(nextNodes, edges);
      });
    },
    [decorateStatuses, edges, maybeGrowRootDuringDrag],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  /**
   * This is the key fix: on drag stop, we call fitRootTightly to snap
   * the wrapper to its optimal size, allowing it to shrink.
   */
  const onNodeDragStop = useCallback(() => {
    setNodes((nds) => fitRootTightly(nds, edges));
  }, [fitRootTightly, edges]);

  const onPaneContextMenu = useCallback((evt: React.MouseEvent) => {
    evt.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    setMenu({ open: true, x: evt.clientX - (rect?.left ?? 0), y: evt.clientY - (rect?.top ?? 0) });
  }, []);

  const closeMenu = useCallback(() => setMenu((m) => ({ ...m, open: false })), []);

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        proOptions={{ hideAttribution: true }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        onPaneContextMenu={onPaneContextMenu}
        connectionLineType={ConnectionLineType.SmoothStep}
        defaultEdgeOptions={{
          type: "transitionEdge",
          markerEnd: { type: MarkerType.ArrowClosed, color: "hsl(var(--foreground))" },
        }}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        className="bg-background"
      >
        <Controls />
        <MiniMap nodeColor={(n) => (n.selected ? "hsl(var(--primary))" : "hsl(var(--border))")} />
        <Background />
      </ReactFlow>

      {menu.open && (
        <div
          style={{ left: menu.x, top: menu.y }}
          className="absolute z-50 rounded-md border bg-popover text-popover-foreground shadow-md"
          onMouseLeave={closeMenu}
        >
          <button
            className="w-full text-left px-3 py-2 hover:bg-muted"
            onClick={() => {
              closeMenu();
              relayout().catch(console.error);
            }}
          >
            Auto layout
          </button>
          <button
            className="w-full text-left px-3 py-2 hover:bg-muted"
            onClick={() => {
              closeMenu();
              fitView({ duration: 300, padding: 0.12 });
            }}
          >
            Fit view
          </button>
        </div>
      )}
    </div>
  );
};

export const StatechartDiagram = (props: DiagramProps) => (
  <ReactFlowProvider>
    <DiagramCanvas {...props} />
  </ReactFlowProvider>
);
