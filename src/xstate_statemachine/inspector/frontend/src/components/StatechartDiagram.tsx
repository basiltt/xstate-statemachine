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
  SelectionMode,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";

import { MachineState } from "@/hooks/useInspectorSocket";
import { getLayoutedElements } from "./statechart/layout";
import {
  PADDING,
  ROOT_HEADER,
  estimateReservedTop,
  EDGE_CLEAR_TOP,
  GROW_PREEMPT,
} from "./statechart/constants";
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

const EDGE_MARGIN = 48;

const DiagramCanvas = ({ machine, activeStateIds }: DiagramProps) => {
  const initialLayout = useMemo(
    () => getLayoutedElements(machine.definition, machine.context),
    [machine.definition, machine.context],
  );

  const containerRef = useRef<HTMLDivElement>(null);

  const reservedTop = useMemo(
    () => estimateReservedTop(machine.context) + EDGE_CLEAR_TOP,
    [machine.context],
  );

  // 👉 Controlled state
  const [nodes, setNodes] = useState(() =>
    initialLayout.nodes.map((n: any) => ({
      ...n,
      ...(n.type === "rootNode"
        ? { dragHandle: ".root-drag-handle", style: { ...(n.style || {}), zIndex: 0 } }
        : {}),
      // make everything draggable, except the synthetic initial marker
      draggable: n.type !== "initialNode",
      selected: activeStateIds.includes(n.id),
    })),
  );
  const [edges, setEdges] = useState(
    (initialLayout.edges as Edge[]).map((e) => ({
      ...e,
      data: { ...(e.data as any), reservedTop },
    })),
  );

  // Context menu state for Auto Layout
  const [menu, setMenu] = useState<{ open: boolean; x: number; y: number }>({
    open: false,
    x: 0,
    y: 0,
  });

  // @ts-ignore
  const { fitView, updateNodeInternals } = useReactFlow();

  // Decorate nodes with UI status for styling (active/current and next-candidate)
  const decorateStatuses = useCallback((list: Node[], eds: Edge[], actives: string[]): Node[] => {
    const activeSet = new Set(actives);
    const nextSet = new Set<string>();
    for (const e of eds) {
      if ((e as any).type !== "transitionEdge") continue;
      if (activeSet.has(e.source) && !String(e.source).includes(".__initial__")) {
        nextSet.add(e.target);
      }
    }
    return list.map((n) => {
      const uiStatus = activeSet.has(n.id) ? "active" : nextSet.has(n.id) ? "next" : undefined;
      return { ...n, data: { ...n.data, uiStatus } } as Node;
    });
  }, []);

  // Utility: compute wrapper bounds around children and edges
  const computeRootBounds = useCallback(
    (allNodes: Node[], eds: Edge[]) => {
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

      const idToNode = new Map(allNodes.map((n) => [n.id, n] as const));
      for (const e of eds) {
        const s = idToNode.get(e.source);
        const t = idToNode.get(e.target);
        if (!s || !t) continue;
        if (s.parentNode !== root.id || t.parentNode !== root.id) continue;
        const sw = ((s as any).width ?? 250) / 2;
        const sh = ((s as any).height ?? 60) / 2;
        const tw = ((t as any).width ?? 250) / 2;
        const th = ((t as any).height ?? 60) / 2;
        const sx = s.position.x + sw;
        const sy = s.position.y + sh;
        const tx = t.position.x + tw;
        const ty = t.position.y + th;
        minX = Math.min(minX, Math.min(sx, tx) - EDGE_MARGIN);
        maxX = Math.max(maxX, Math.max(sx, tx) + EDGE_MARGIN);
        minY = Math.min(minY, Math.min(sy, ty) - EDGE_MARGIN);
        maxY = Math.max(maxY, Math.max(sy, ty) + EDGE_MARGIN);
      }

      const width = Math.max(maxX - minX + PADDING, 200);
      const height = Math.max(maxY - minY + PADDING + reservedTop - ROOT_HEADER, 140 + reservedTop);

      return { minX, minY, maxX, maxY, width, height };
    },
    [reservedTop],
  );

  // Expand-only wrapper during drag if children approach edges or reserved top
  const maybeGrowRootDuringDrag = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const rootIndex = currentNodes.findIndex((n) => n.type === "rootNode");
      if (rootIndex < 0) return currentNodes;
      const root = currentNodes[rootIndex];

      const tight = computeRootBounds(currentNodes, eds);
      if (!tight) return currentNodes;

      const currWidth = (root.style as any)?.width ?? (root as any).width ?? tight.width;
      const currHeight = (root.style as any)?.height ?? (root as any).height ?? tight.height;

      // preemptively move the wrapper before nodes/edges hit the inner gap
      const leftThreshold = PADDING / 2 + GROW_PREEMPT;
      const topThreshold = PADDING / 2 + reservedTop + GROW_PREEMPT;
      const needLeftPad = tight.minX < leftThreshold;
      const needTopPad = tight.minY < topThreshold;
      const dx = needLeftPad ? tight.minX - leftThreshold : 0;
      const dy = needTopPad ? tight.minY - topThreshold : 0;

      // also preemptively increase right/bottom size so gap feels consistent
      const nextWidth = Math.max(currWidth, tight.width + GROW_PREEMPT * 2);
      const nextHeight = Math.max(currHeight, tight.height + GROW_PREEMPT * 2);

      if (!needLeftPad && !needTopPad && nextWidth === currWidth && nextHeight === currHeight) {
        return currentNodes; // no-op
      }

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          return {
            ...n,
            position: { x: n.position.x + dx, y: n.position.y + dy },
            style: { ...(n.style as any), width: nextWidth, height: nextHeight, zIndex: 0 },
            dragHandle: ".root-drag-handle",
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
    [computeRootBounds, reservedTop, updateNodeInternals],
  );

  // Tight fit wrapper after drag stop or structural updates.
  const fitRootTightly = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const rootIndex = currentNodes.findIndex((n) => n.type === "rootNode");
      if (rootIndex < 0) return currentNodes;
      const root = currentNodes[rootIndex];

      const tight = computeRootBounds(currentNodes, eds);
      if (!tight) return currentNodes;

      const dx = tight.minX - PADDING / 2;
      const dy = tight.minY - (PADDING / 2 + reservedTop);

      const newRoot = {
        ...root,
        position: { x: root.position.x + dx, y: root.position.y + dy },
        style: { ...(root.style as any), width: tight.width, height: tight.height, zIndex: 0 },
        dragHandle: ".root-drag-handle",
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
    [computeRootBounds, reservedTop, updateNodeInternals],
  );

  // Re-run dagre auto layout and apply wrapper fit
  const relayout = useCallback(() => {
    const layout = getLayoutedElements(machine.definition, machine.context);
    // Decorate and add reservedTop to edges
    const laidNodes = decorateStatuses(
      layout.nodes.map((n: any) => ({
        ...n,
        ...(n.type === "rootNode"
          ? { dragHandle: ".root-drag-handle", style: { ...(n.style || {}), zIndex: 0 } }
          : {}),
        draggable: n.type !== "initialNode",
      })),
      layout.edges as Edge[],
      activeStateIds,
    );
    const laidEdges = (layout.edges as Edge[]).map((e) => ({
      ...e,
      data: { ...(e.data as any), reservedTop },
    }));

    setNodes(() => fitRootTightly(laidNodes, laidEdges));
    setEdges(laidEdges);
    setTimeout(() => fitView({ duration: 300, padding: 0.12 }), 0);
  }, [
    machine.definition,
    machine.context,
    decorateStatuses,
    activeStateIds,
    fitRootTightly,
    reservedTop,
    fitView,
  ]);

  // Reset positions & selections if the machine changes
  useEffect(() => {
    setNodes(
      decorateStatuses(
        initialLayout.nodes.map((n: any) => ({
          ...n,
          ...(n.type === "rootNode"
            ? { dragHandle: ".root-drag-handle", style: { ...(n.style || {}), zIndex: 0 } }
            : {}),
          draggable: n.type !== "initialNode",
          selected: activeStateIds.includes(n.id),
        })),
        initialLayout.edges as Edge[],
        activeStateIds,
      ),
    );
    setEdges(
      (initialLayout.edges as Edge[]).map((e) => ({
        ...e,
        data: { ...(e.data as any), reservedTop },
      })),
    );
    const id = setTimeout(() => {
      setNodes((prev) => fitRootTightly(prev, initialLayout.edges as Edge[]));
      fitView({ duration: 400, padding: 0.1 });
    }, 50);
    return () => clearTimeout(id);
  }, [initialLayout, activeStateIds, fitRootTightly, fitView, decorateStatuses, reservedTop]);

  // Keep selection highlighting & statuses in sync
  useEffect(() => {
    setNodes((prev) =>
      decorateStatuses(
        prev.map((n) => ({ ...n, selected: activeStateIds.includes(n.id) })),
        edges,
        activeStateIds,
      ),
    );
  }, [activeStateIds, edges, decorateStatuses]);

  // Controlled handlers
  const onNodesChange = useCallback(
    (changes: NodeChange[]) =>
      setNodes((nds) => {
        const next = applyNodeChanges(changes, nds);
        const root = next.find((n) => n.type === "rootNode");
        if (!root) return next;
        const changedIds = new Set(changes.map((c) => ("id" in c ? (c as any).id : undefined)));
        const childChanged = next.some((n) => n.parentNode === root.id && changedIds.has(n.id));
        const adjusted = childChanged ? fitRootTightly(next, edges) : next;
        return decorateStatuses(adjusted, edges, activeStateIds);
      }),
    [fitRootTightly, edges, activeStateIds, decorateStatuses],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) =>
      setEdges((eds) =>
        applyEdgeChanges(changes, eds).map((e: any) => ({
          ...e,
          data: { ...(e.data || {}), reservedTop },
        })),
      ),
    [reservedTop],
  );

  const onNodeDrag = useCallback(
    (_evt: any, dragging?: Node) => {
      setNodes((prev) => {
        // soft-protect the top context band while dragging
        const next =
          dragging && dragging.type !== "rootNode"
            ? prev.map((n) => {
                if (n.id === dragging.id) {
                  const minY = reservedTop + 4;
                  const y = Math.max(n.position.y, minY);
                  return { ...n, position: { x: n.position.x, y } } as Node;
                }
                return n;
              })
            : prev;
        return maybeGrowRootDuringDrag(next, edges);
      });
    },
    [maybeGrowRootDuringDrag, edges, reservedTop],
  );

  const onNodeDragStop = useCallback(
    (_evt: any, node?: Node) => {
      if (!node) return;
      if (node.type !== "rootNode") {
        setNodes((prev) => fitRootTightly(prev, edges));
      }
    },
    [fitRootTightly, edges],
  );

  const onPaneContextMenu = useCallback((evt: any) => {
    evt.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    const x = rect ? evt.clientX - rect.left : evt.clientX;
    const y = rect ? evt.clientY - rect.top : evt.clientY;
    setMenu({ open: true, x, y });
  }, []);

  const closeMenu = useCallback(() => setMenu((m) => ({ ...m, open: false })), []);

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        proOptions={{ hideAttribution: true }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        selectionOnDrag
        // enable panning with middle mouse on the pane
        panOnDrag={[1]}
        panOnScroll={false}
        onNodeDrag={onNodeDrag}
        onNodeDragStop={onNodeDragStop}
        onPaneContextMenu={onPaneContextMenu}
        selectionMode={SelectionMode.Partial}
        connectionLineType={ConnectionLineType.SmoothStep}
        defaultEdgeOptions={{
          type: "transitionEdge",
          markerEnd: { type: MarkerType.ArrowClosed },
        }}
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
              relayout();
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
