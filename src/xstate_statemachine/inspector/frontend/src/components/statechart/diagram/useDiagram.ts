// src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/useDiagram.ts

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import {
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  useReactFlow,
  useUpdateNodeInternals,
  type Viewport,
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
  autoFitAfterDrag?: boolean;
};

const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

export const useDiagram = ({
  machine,
  activeStateIds,
  autoFitAfterDrag = true,
}: UseDiagramProps) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [hasSavedPositions, setHasSavedPositions] = useState(false);

  const latestNodesRef = useRef<Node[]>([]);
  useEffect(() => {
    latestNodesRef.current = nodes;
  }, [nodes]);

  const { fitView, getNodes, getViewport } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const storageKey = useMemo(() => `xsi.positions.${machine.id}`, [machine.id]);
  const viewportKey = useMemo(() => `xsi.viewport.${machine.id}`, [machine.id]);

  // Read the last saved viewport synchronously for initial mount so ReactFlow can use it via defaultViewport
  const initialViewport = useMemo<Viewport | null>(() => {
    try {
      const raw = localStorage.getItem(viewportKey);
      if (!raw) return null;
      const vp = JSON.parse(raw);
      if (vp && typeof vp.x === "number" && typeof vp.y === "number" && typeof vp.zoom === "number")
        return vp as Viewport;
    } catch {}
    return null;
  }, [viewportKey]);

  // Keep a controlled viewport state to ensure ReactFlow always honors the saved position
  const [viewport, setViewportState] = useState<Viewport | undefined>(initialViewport ?? undefined);

  const reservedTop = useMemo(
    () =>
      Math.max(estimateReservedTop(machine.context) + EDGE_CLEAR_TOP, ROOT_HEADER + EDGE_CLEAR_TOP),
    [machine.context],
  );
  const headerGuardTop = useMemo(() => calculateHeaderGuardTop(reservedTop), [reservedTop]);

  /* ---------------------- Position persistence helpers ---------------------- */
  const loadSavedPositions = useCallback((): Map<string, { x: number; y: number }> => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return new Map();
      const obj = JSON.parse(raw) as Record<string, { x: number; y: number }>;
      return new Map(Object.entries(obj));
    } catch {
      return new Map();
    }
  }, [storageKey]);

  const applySavedPositions = useCallback(
    (list: Node[]): Node[] => {
      const saved = loadSavedPositions();
      if (saved.size === 0) return list;
      return list.map((n) => {
        const s = saved.get(n.id);
        if (!s) return n;
        return { ...n, position: { x: s.x, y: s.y } };
      });
    },
    [loadSavedPositions],
  );

  const savePositionsFromGraph = useCallback(() => {
    try {
      const map: Record<string, { x: number; y: number }> = {};
      for (const n of getNodes()) {
        map[n.id] = { x: n.position.x, y: n.position.y };
      }
      localStorage.setItem(storageKey, JSON.stringify(map));
    } catch {
      // ignore
    }
  }, [getNodes, storageKey]);

  // Immediate saver that uses a provided snapshot of nodes (preferred for end-of-drag)
  const savePositionsSnapshot = useCallback(
    (list: Node[]) => {
      try {
        const map: Record<string, { x: number; y: number }> = {};
        for (const n of list) {
          map[n.id] = { x: n.position.x, y: n.position.y };
        }
        localStorage.setItem(storageKey, JSON.stringify(map));
      } catch {
        // ignore
      }
    },
    [storageKey],
  );

  /* ---------------------- Viewport persistence helpers ---------------------- */
  const loadSavedViewport = useCallback((): Viewport | null => {
    try {
      const raw = localStorage.getItem(viewportKey);
      if (!raw) return null;
      const vp = JSON.parse(raw) as Viewport;
      if (
        typeof vp === "object" &&
        vp !== null &&
        typeof vp.x === "number" &&
        typeof vp.y === "number" &&
        typeof vp.zoom === "number"
      )
        return vp;
      return null;
    } catch {
      return null;
    }
  }, [viewportKey]);

  const saveViewport = useCallback(
    (vp?: Viewport) => {
      try {
        const toSave = vp ?? getViewport?.();
        if (!toSave) return;
        localStorage.setItem(viewportKey, JSON.stringify(toSave));
      } catch {
        // ignore
      }
    },
    [viewportKey, getViewport],
  );

  /* ---------------------- Status decoration helpers ---------------------- */

  /** Tag nodes with `data.uiStatus` = 'active' | 'next' (or undefined). */
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

  /** Tag edges as `data.uiActive` when leaving an active node (and optionally from next nodes). */
  const decorateEdgeStatuses = useCallback(
    (eds: Edge[]): Edge[] => {
      const activeSet = new Set(activeStateIds);
      const nextSet = new Set<string>();
      for (const e of eds) if (activeSet.has(e.source)) nextSet.add(e.target);

      return eds.map((e) => ({
        ...e,
        data: {
          ...(e.data ?? {}),
          // highlight edges leaving an active node, and edges leaving nodes that are "next"
          uiActive: activeSet.has(e.source) || nextSet.has(e.source),
        },
      }));
    },
    [activeStateIds],
  );

  /* --------------------------- Layout utilities -------------------------- */

  const ensureUnderRoot = useCallback((nds: Node[]): Node[] => {
    const root = nds.find((n) => n.type === "rootNode");
    if (!root) return nds;
    return nds.map((n) =>
      n.id === root.id ? n : { ...n, parentId: root.id, extent: "parent", draggable: true },
    );
  }, []);

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
      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!root || !tight) return currentNodes;

      let next = currentNodes;

      // 1) Keep header area clear
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

      // 2) Grow the root slightly so contents have breathing room
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
    async (eds: Edge[], opts?: { adjustPositions?: boolean }) => {
      await nextFrame();
      await nextFrame();

      const ids = getNodes()
        .filter((n) => n.type !== "rootNode")
        .map((n) => n.id);
      ids.forEach((id) => updateNodeInternals(id));

      await nextFrame();
      // Only adjust node positions if explicitly requested (default: when no saved positions)
      const shouldAdjust = opts?.adjustPositions ?? !hasSavedPositions;
      if (shouldAdjust) {
        setNodes((prev) => fitRootTightly(prev, eds));
        await nextFrame();
      }

      fitView({ duration: 500, padding: 0.18, includeHiddenNodes: true });
      // Persist viewport after programmatic fit
      setTimeout(() => saveViewport(), 0);
    },
    [getNodes, updateNodeInternals, fitRootTightly, fitView, saveViewport, hasSavedPositions],
  );

  /* ------------------------------- Relayout ------------------------------- */

  const relayout = useCallback(async () => {
    const { nodes: laidOutNodes, edges: laidOutEdges } = await getLayoutedElements(
      machine.definition,
      machine.context,
    );

    // Tag edges first (so node "next" status can be derived from them)
    const edgesWithStatus = decorateEdgeStatuses(laidOutEdges);

    // Parent all under root, then set node statuses (active/next)
    const parented = ensureUnderRoot(laidOutNodes);
    const withStatus = decorateStatuses(parented, edgesWithStatus);

    // Check if we have any saved positions for this machine
    const hasSaved = loadSavedPositions().size > 0;
    setHasSavedPositions(hasSaved);

    // Apply saved positions if present
    const positioned = applySavedPositions(withStatus);

    // Only guard/grow when we don't already have user-defined positions
    const nextNodes = hasSaved ? positioned : guardHeaderAndMaybeGrow(positioned, edgesWithStatus);

    setEdges(edgesWithStatus);
    setNodes(nextNodes);

    // Restore viewport if previously saved; otherwise, run a one-time fit
    const savedVp = loadSavedViewport();
    if (initialViewport) {
      // Using controlled viewport; nothing to do here
      setViewportState(initialViewport);
    } else if (savedVp) {
      setViewportState(savedVp);
    } else {
      tightenAndFitWhenReady(edgesWithStatus, { adjustPositions: !hasSaved }).catch(console.error);
    }
  }, [
    machine.definition,
    machine.context,
    ensureUnderRoot,
    decorateStatuses,
    decorateEdgeStatuses,
    applySavedPositions,
    guardHeaderAndMaybeGrow,
    tightenAndFitWhenReady,
    loadSavedPositions,
    loadSavedViewport,
    initialViewport,
  ]);

  useEffect(() => {
    relayout().catch(console.error);
  }, [relayout]);

  // When active states shift, re-decorate nodes and edges without recomputing layout
  useEffect(() => {
    setEdges((prev) => decorateEdgeStatuses(prev));
    setNodes((prev) => decorateStatuses(prev, edges));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeStateIds, decorateStatuses, decorateEdgeStatuses]);

  /* --------------------------- RF change handlers ------------------------- */

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      let isDrop = false;
      for (const c of changes)
        if (c.type === "position" && !c.dragging) {
          isDrop = true;
          break;
        }

      setNodes((curr) => {
        const next = applyNodeChanges(changes, curr);
        const guarded = guardHeaderAndMaybeGrow(next, edges);
        if (isDrop) {
          // Save immediately on drop using the computed positions
          savePositionsSnapshot(guarded);
          // Also save current viewport so reload opens where the user left it
          saveViewport();
        }
        const dragging = changes.some((c) => c.type === "position" && c.dragging);
        return dragging ? guarded : decorateStatuses(guarded, edges);
      });
    },
    [edges, decorateStatuses, guardHeaderAndMaybeGrow, savePositionsSnapshot, saveViewport],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) =>
      setEdges((eds) => decorateEdgeStatuses(applyEdgeChanges(changes, eds))),
    [decorateEdgeStatuses],
  );

  const onNodeDragStop = useCallback(() => {
    // Do not re-tighten/rebase node positions on drag stop; respect user placement.
    setNodes((nds) => {
      const ids = nds.filter((n) => n.type !== "rootNode").map((n) => n.id);
      setTimeout(() => ids.forEach((id) => updateNodeInternals(id)), 0);
      return nds;
    });

    // Save immediately using the latest snapshot of nodes and the viewport
    if (latestNodesRef.current.length) {
      savePositionsSnapshot(latestNodesRef.current);
    } else {
      savePositionsFromGraph();
    }
    saveViewport();

    if (autoFitAfterDrag) {
      // Fit the viewport only; do not change node positions
      tightenAndFitWhenReady(edges, { adjustPositions: false }).catch(console.error);
    }
  }, [
    edges,
    updateNodeInternals,
    tightenAndFitWhenReady,
    autoFitAfterDrag,
    savePositionsFromGraph,
    savePositionsSnapshot,
    saveViewport,
  ]);

  // Persist viewport when panning/zooming stops
  const onMoveEnd = useCallback(
    (_: any, vp: Viewport) => {
      if (vp) setViewportState(vp);
      saveViewport(vp);
    },
    [saveViewport],
  );

  // ReactFlow controlled viewport change handler (fires for user and programmatic changes)
  const onViewportChange = useCallback((vp: Viewport) => {
    setViewportState(vp);
  }, []);

  // Return values to be used by the view component
  return {
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
    viewport,
    onViewportChange,
  };
};
