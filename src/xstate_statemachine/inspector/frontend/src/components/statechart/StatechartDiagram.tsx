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

import { getLayoutedElements } from "./layout";
import {
  EDGE_CLEAR_TOP,
  estimateReservedTop,
  GRID_SIZE,
  GROW_PREEMPT,
  PADDING,
  ROOT_HEADER,
} from "./constants";

import { CompoundStateNode, EventNode, InitialNode, RootNode, StateNode } from "./nodes";
import { TransitionEdge } from "@/components/statechart/edges.tsx";
import { MachineState } from "@/hooks/useInspectorSocket.ts";

const nodeTypes = {
  rootNode: RootNode,
  stateNode: StateNode,
  compoundStateNode: CompoundStateNode,
  eventNode: EventNode,
  initialNode: InitialNode,
};
const edgeTypes = { transitionEdge: TransitionEdge };

const EDGE_MARGIN = 48;

type DiagramProps = {
  machine: MachineState;
  activeStateIds: string[];
};

const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

const DiagramCanvas = ({ machine, activeStateIds }: DiagramProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  // @ts-ignore
  const didInitialFit = useRef(false);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [menu, setMenu] = useState<{ open: boolean; x: number; y: number }>({
    open: false,
    x: 0,
    y: 0,
  });

  const { fitView, getNodes } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const reservedTop = useMemo(
    () =>
      Math.max(estimateReservedTop(machine.context) + EDGE_CLEAR_TOP, ROOT_HEADER + EDGE_CLEAR_TOP),
    [machine.context],
  );
  const headerGuardTop = useMemo(() => reservedTop + PADDING / 2, [reservedTop]);

  /* ---------------------- UI status highlighting ---------------------- */
  const decorateStatuses = useCallback(
    (list: Node[], eds: Edge[]): Node[] => {
      const activeSet = new Set(activeStateIds);
      const nextSet = new Set<string>();
      for (const e of eds) if (activeSet.has(e.source)) nextSet.add(e.target);
      return list.map((n) => ({
        ...n,
        data: {
          ...n.data,
          uiStatus: activeSet.has(n.id) ? "active" : nextSet.has(n.id) ? "next" : undefined,
        },
      }));
    },
    [activeStateIds],
  );

  const ensureUnderRoot = useCallback((nds: Node[]): Node[] => {
    const root = nds.find((n) => n.type === "rootNode");
    if (!root) return nds;
    return nds.map((n) =>
      n.id === root.id ? n : { ...n, parentId: root.id, extent: "parent", draggable: true },
    );
  }, []);

  /* ---------------------- Bounds & wrapper helpers ---------------------- */
  const computeRootBounds = useCallback(
    (allNodes: Node[], eds: Edge[]) => {
      const root = allNodes.find((n) => n.type === "rootNode");
      if (!root) return null;
      const children = allNodes.filter((n) => n.parentId === root.id);
      if (!children.length) return null;

      let minX = Infinity,
        minY = Infinity,
        maxX = -Infinity,
        maxY = -Infinity;

      for (const ch of children) {
        const w = ch.width ?? 0;
        const h = ch.height ?? 0;
        minX = Math.min(minX, ch.position.x);
        minY = Math.min(minY, ch.position.y);
        maxX = Math.max(maxX, ch.position.x + w);
        maxY = Math.max(maxY, ch.position.y + h);
      }

      // edge span
      const map = new Map(allNodes.map((n) => [n.id, n] as const));
      for (const e of eds) {
        const s = map.get(e.source);
        const t = map.get(e.target);
        if (!s || !t || s.parentId !== root.id || t.parentId !== root.id) continue;
        const sx = s.position.x + (s.width ?? 0) / 2;
        const sy = s.position.y + (s.height ?? 0) / 2;
        const tx = t.position.x + (t.width ?? 0) / 2;
        const ty = t.position.y + (t.height ?? 0) / 2;
        minX = Math.min(minX, Math.min(sx, tx) - EDGE_MARGIN);
        maxX = Math.max(maxX, Math.max(sx, tx) + EDGE_MARGIN);
        minY = Math.min(minY, Math.min(sy, ty) - EDGE_MARGIN);
        maxY = Math.max(maxY, Math.max(sy, ty) + EDGE_MARGIN);
      }

      // never start above header band
      minY = Math.max(minY, headerGuardTop);

      const width = Math.max(maxX - minX + PADDING + 72, 320);
      const height = Math.max(
        maxY - minY + PADDING + 80 + reservedTop - ROOT_HEADER,
        200 + reservedTop,
      );

      return { minX, minY, width, height };
    },
    [reservedTop, headerGuardTop],
  );

  const guardHeaderAndMaybeGrow = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!root || !tight) return currentNodes;

      let next = currentNodes;

      // push graph down if it's intruding into header band
      const overlap = headerGuardTop - tight.minY;
      if (overlap > 0) {
        next = next.map((n) => {
          if (n.id === root.id)
            return { ...n, position: { x: n.position.x, y: n.position.y - overlap } };
          if (n.parentId === root.id)
            return { ...n, position: { x: n.position.x, y: n.position.y + overlap } };
          return n;
        });
      }

      const t2 = computeRootBounds(next, eds) ?? tight;

      // grow wrapper if needed
      const cw = (root.style as any)?.width ?? root.width ?? t2.width;
      const ch = (root.style as any)?.height ?? root.height ?? t2.height;
      const nw = Math.max(cw, t2.width + (GROW_PREEMPT ?? 40));
      const nh = Math.max(ch, t2.height + (GROW_PREEMPT ?? 40));

      if (nw !== cw || nh !== ch) {
        next = next.map((n) =>
          n.id === root.id ? { ...n, style: { ...n.style, width: nw, height: nh } } : n,
        );
      }

      updateNodeInternals(root.id);
      return next;
    },
    [computeRootBounds, headerGuardTop, updateNodeInternals],
  );

  const fitRootTightly = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!root || !tight) return currentNodes;

      const dx = tight.minX - PADDING / 2;
      const dy = tight.minY - headerGuardTop;

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          return {
            ...n,
            position: { x: root.position.x + dx, y: root.position.y + dy },
            style: { ...n.style, width: tight.width, height: tight.height },
          };
        }
        if (n.parentId === root.id) {
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } };
        }
        return n;
      });

      updateNodeInternals(root.id);
      return updated;
    },
    [computeRootBounds, headerGuardTop, updateNodeInternals],
  );

  /* ---------------------- Measure → tighten → center ---------------------- */
  const tightenAndFitWhenReady = useCallback(
    async (eds: Edge[]) => {
      // allow React & RF to mount nodes
      await nextFrame();
      await nextFrame();

      // force a measurement pass for auto-height nodes
      const ids = getNodes()
        .filter((n) => n.type !== "rootNode")
        .map((n) => n.id);
      ids.forEach((id) => updateNodeInternals(id));

      // wait once more for sizes to settle
      await nextFrame();

      setNodes((prev) => fitRootTightly(prev, eds));

      // finally center & fit
      await nextFrame();
      fitView({ duration: 500, padding: 0.18, includeHiddenNodes: true });
    },
    [getNodes, updateNodeInternals, fitRootTightly, fitView],
  );

  /* ---------------------- Layout pipeline ---------------------- */
  const relayout = useCallback(async () => {
    const { nodes: laidOutNodes, edges: laidOutEdges } = await getLayoutedElements(
      machine.definition,
      machine.context,
    );

    const parented = ensureUnderRoot(laidOutNodes);
    const withStatus = decorateStatuses(parented, laidOutEdges);

    setEdges(laidOutEdges);
    setNodes(withStatus);

    // initial fit (and subsequent "Auto layout")
    tightenAndFitWhenReady(laidOutEdges).catch(console.error);
  }, [
    machine.definition,
    machine.context,
    ensureUnderRoot,
    decorateStatuses,
    tightenAndFitWhenReady,
  ]);

  useEffect(() => {
    relayout().catch(console.error);
  }, [relayout]);

  // Keep highlights in sync
  useEffect(() => {
    setNodes((prev) => decorateStatuses(prev, edges));
  }, [activeStateIds, edges, decorateStatuses]);

  /* ---------------------- RF event handlers ---------------------- */
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((curr) => {
        const next = applyNodeChanges(changes, curr);
        const guarded = guardHeaderAndMaybeGrow(next, edges);
        const dragging = changes.some((c) => c.type === "position" && c.dragging);
        return dragging ? guarded : decorateStatuses(guarded, edges);
      });
    },
    [edges, decorateStatuses, guardHeaderAndMaybeGrow],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  const onNodeDragStop = useCallback(() => {
    setNodes((nds) => {
      const tight = fitRootTightly(nds, edges);
      const ids = tight.filter((n) => n.type !== "rootNode").map((n) => n.id);
      setTimeout(() => ids.forEach((id) => updateNodeInternals(id)), 0);
      return tight;
    });
    tightenAndFitWhenReady(edges).catch(console.error);
  }, [fitRootTightly, edges, updateNodeInternals, tightenAndFitWhenReady]);

  const onPaneContextMenu = useCallback((evt: React.MouseEvent) => {
    evt.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    setMenu({ open: true, x: evt.clientX - (rect?.left ?? 0), y: evt.clientY - (rect?.top ?? 0) });
  }, []);
  const closeMenu = useCallback(() => setMenu((m) => ({ ...m, open: false })), []);

  /* ---------------------- Render ---------------------- */
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
        connectionLineType={ConnectionLineType.Step}
        defaultEdgeOptions={{
          type: "transitionEdge",
          markerEnd: { type: MarkerType.ArrowClosed, color: "hsl(var(--foreground))" },
        }}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        snapToGrid
        snapGrid={[GRID_SIZE ?? 8, GRID_SIZE ?? 8]}
        className="bg-background"
        onPaneContextMenu={onPaneContextMenu}
      >
        <Controls />
        <MiniMap />
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
              tightenAndFitWhenReady(edges).catch(console.error);
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
