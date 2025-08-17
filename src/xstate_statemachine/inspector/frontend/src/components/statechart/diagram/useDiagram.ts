// src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/useDiagram.ts

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  useReactFlow,
  useUpdateNodeInternals,
} from "reactflow";

import { getLayoutedElements } from "@/components/statechart/layout";
import { MachineState } from "@/hooks/useInspectorSocket.ts";
import {
  EDGE_CLEAR_TOP,
  EDGE_MARGIN,
  estimateReservedTop,
  GROW_PREEMPT,
  headerGuardTop as calculateHeaderGuardTop,
  PADDING,
  ROOT_HEADER,
} from "@/components/statechart/constants";

type UseDiagramProps = {
  machine: MachineState;
  activeStateIds: string[];
};

const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

export const useDiagram = ({ machine, activeStateIds }: UseDiagramProps) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const { fitView, getNodes } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const reservedTop = useMemo(
    () =>
      Math.max(estimateReservedTop(machine.context) + EDGE_CLEAR_TOP, ROOT_HEADER + EDGE_CLEAR_TOP),
    [machine.context],
  );
  const headerGuardTop = useMemo(() => calculateHeaderGuardTop(reservedTop), [reservedTop]);

  /* ---------------------- Logic moved from component ---------------------- */

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

  const computeRootBounds = useCallback(
    (allNodes: Node[], eds: Edge[]) => {
      // ... (exact same implementation as in the original file)
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
      // ... (exact same implementation)
      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!root || !tight) return currentNodes;
      let next = currentNodes;
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
      // ... (exact same implementation)
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

  const tightenAndFitWhenReady = useCallback(
    async (eds: Edge[]) => {
      // ... (exact same implementation)
      await nextFrame();
      await nextFrame();
      const ids = getNodes()
        .filter((n) => n.type !== "rootNode")
        .map((n) => n.id);
      ids.forEach((id) => updateNodeInternals(id));
      await nextFrame();
      setNodes((prev) => fitRootTightly(prev, eds));
      await nextFrame();
      fitView({ duration: 500, padding: 0.18, includeHiddenNodes: true });
    },
    [getNodes, updateNodeInternals, fitRootTightly, fitView],
  );

  const relayout = useCallback(async () => {
    const { nodes: laidOutNodes, edges: laidOutEdges } = await getLayoutedElements(
      machine.definition,
      machine.context,
    );
    const parented = ensureUnderRoot(laidOutNodes);
    const withStatus = decorateStatuses(parented, laidOutEdges);
    setEdges(laidOutEdges);
    setNodes(withStatus);
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

  useEffect(() => {
    setNodes((prev) => decorateStatuses(prev, edges));
  }, [activeStateIds, edges, decorateStatuses]);

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

  // Return values to be used by the view component
  return {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onNodeDragStop,
    relayout,
    tightenAndFitWhenReady,
  };
};
