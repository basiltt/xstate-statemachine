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
  estimateReservedTop,
  headerGuardTop as calculateHeaderGuardTop,
  ROOT_HEADER,
} from "@/components/statechart/constants";

import { usePositionsPersistence } from "./hooks/usePositionsPersistence";
import { useViewportPersistence } from "./hooks/useViewportPersistence";
import { useStatusDecorators } from "./hooks/useStatusDecorators";
import { useLiveEdgeRouting } from "./hooks/useLiveEdgeRouting";
import { defaultRouterConfig, routeEdges } from "./hooks/router";
import { useWrapperSizing } from "./hooks/useWrapperSizing";

type UseDiagramProps = {
  machine: MachineState;
  activeStateIds: string[];
  autoFitAfterDrag?: boolean;
};

export const useDiagram = ({
  machine,
  activeStateIds,
  autoFitAfterDrag = false,
}: UseDiagramProps) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [hasSavedPositions, setHasSavedPositions] = useState(false);

  const latestNodesRef = useRef<Node[]>([]);
  useEffect(() => {
    latestNodesRef.current = nodes;
  }, [nodes]);

  // Track latest edges to avoid stale closures in effects
  const latestEdgesRef = useRef<Edge[]>([]);
  useEffect(() => {
    latestEdgesRef.current = edges;
  }, [edges]);

  const suppressNextDropRef = useRef(false);
  const lastDraggingIdRef = useRef<string | null>(null);

  const { fitView, getNodes, getViewport } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const storageKey = useMemo(() => `xsi.positions.${machine.id}`, [machine.id]);
  const viewportKey = useMemo(() => `xsi.viewport.${machine.id}`, [machine.id]);

  // Debounce reservedTop calculation to prevent flickering from frequent context changes
  const [debouncedReservedTop, setDebouncedReservedTop] = useState(() =>
    Math.max(estimateReservedTop(machine.context) + EDGE_CLEAR_TOP, ROOT_HEADER + EDGE_CLEAR_TOP),
  );

  useEffect(() => {
    const newReservedTop = Math.max(
      estimateReservedTop(machine.context) + EDGE_CLEAR_TOP,
      ROOT_HEADER + EDGE_CLEAR_TOP,
    );

    // Only update if the change is significant (> 2px) to prevent micro-oscillations
    if (Math.abs(newReservedTop - debouncedReservedTop) > 2) {
      const timeoutId = setTimeout(() => {
        setDebouncedReservedTop(newReservedTop);
      }, 100); // 100ms debounce
      return () => clearTimeout(timeoutId);
    }
  }, [machine.context, debouncedReservedTop]);

  const headerGuardTop = useMemo(
    () => calculateHeaderGuardTop(debouncedReservedTop),
    [debouncedReservedTop],
  );

  // --- Hooks
  const { initialViewport, viewport, setViewportState, loadSavedViewport, saveViewport } =
    useViewportPersistence(viewportKey, getViewport);
  const { loadSavedPositions, applySavedPositions, savePositionsFromGraph, savePositionsSnapshot } =
    usePositionsPersistence(storageKey, getNodes);
  const { decorateStatuses, decorateEdgeStatuses } = useStatusDecorators(activeStateIds);
  const { recomputeEdgeHandles } = useLiveEdgeRouting();
  const {
    ensureUnderRoot,
    guardHeaderAndMaybeGrow,
    fitRootTightly,
    tightenAndFitWhenReady,
    withHeaderClamp,
  } = useWrapperSizing({
    reservedTop: debouncedReservedTop,
    headerGuardTop,
    fitView,
    getNodes,
    updateNodeInternals,
    saveViewport,
    hasSavedPositions,
  });

  // ------------------------------- Relayout -------------------------------
  const relayout = useCallback(
    async (opts?: { resetSavedPositions?: boolean }) => {
      if (opts?.resetSavedPositions) {
        try {
          localStorage.removeItem(storageKey);
        } catch {}
        setHasSavedPositions(false);
      }

      const { nodes: laidOutNodes, edges: laidOutEdges } = await getLayoutedElements(
        machine.definition,
        machine.context,
      );
      console.log("Laid out elements:", { laidOutNodes, laidOutEdges });

      // Route deterministic orthogonal edges with waypoints
      const { edges: routed } = routeEdges(laidOutNodes, laidOutEdges, defaultRouterConfig);
      const edgesWithStatus = decorateEdgeStatuses(routed as Edge[]);
      const parented = ensureUnderRoot(laidOutNodes);
      const withStatus = decorateStatuses(parented, edgesWithStatus);

      const hasSaved = opts?.resetSavedPositions ? false : loadSavedPositions().size > 0;
      setHasSavedPositions(hasSaved);

      const positioned = hasSaved ? applySavedPositions(withStatus) : withStatus;
      const nextNodes = hasSaved
        ? positioned
        : guardHeaderAndMaybeGrow(positioned, edgesWithStatus);
      const nextEdges = withHeaderClamp(edgesWithStatus, nextNodes);

      setEdges(nextEdges);
      setNodes(nextNodes);

      if (opts?.resetSavedPositions) savePositionsSnapshot(nextNodes);

      const savedVp = loadSavedViewport();
      if (initialViewport) setViewportState(initialViewport);
      else if (savedVp) setViewportState(savedVp);
      else tightenAndFitWhenReady(nextEdges, { adjustPositions: !hasSaved }).catch(console.error);
    },
    [
      machine.definition,
      // NOTE: Deliberately exclude machine.context to avoid full relayout on frequent context updates
      ensureUnderRoot,
      decorateStatuses,
      decorateEdgeStatuses,
      applySavedPositions,
      guardHeaderAndMaybeGrow,
      tightenAndFitWhenReady,
      loadSavedPositions,
      loadSavedViewport,
      initialViewport,
      withHeaderClamp,
      savePositionsSnapshot,
      storageKey,
    ],
  );

  useEffect(() => {
    relayout().catch(console.error);
  }, [relayout]);

  // When active states shift, re-decorate nodes and edges without recomputing layout
  useEffect(() => {
    setEdges((prev) => decorateEdgeStatuses(prev));
    setNodes((prev) => decorateStatuses(prev, latestEdgesRef.current));
  }, [activeStateIds, decorateStatuses, decorateEdgeStatuses]);

  // When debouncedReservedTop changes, adjust wrapper/clamps only
  useEffect(() => {
    setNodes((curr) => {
      const adjusted = guardHeaderAndMaybeGrow(curr, latestEdgesRef.current);
      setEdges((eds) => withHeaderClamp(eds, adjusted));
      return adjusted;
    });
  }, [debouncedReservedTop, guardHeaderAndMaybeGrow, withHeaderClamp]);

  /* --------------------------- RF change handlers ------------------------- */
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      let isDrop = false;
      const draggingIds = new Set<string>();
      const changedIds = new Set<string>();
      for (const c of changes) {
        if (c.type === "position") {
          changedIds.add(c.id);
          if (c.dragging) {
            draggingIds.add(c.id);
            lastDraggingIdRef.current = c.id;
          } else isDrop = true;
        }
      }

      setNodes((curr) => {
        const next = applyNodeChanges(changes, curr);
        const dragging = changes.some((c) => c.type === "position" && c.dragging);

        if (dragging) {
          // While dragging, keep the wrapper stable to avoid flickering
          // and temporary disappearance of nodes. Only recompute edge
          // handles; defer wrapper adjustments until drag end.
          setEdges((eds) => withHeaderClamp(recomputeEdgeHandles(eds, next, draggingIds), next));
          return decorateStatuses(next, edges);
        }

        if (isDrop) {
          if (suppressNextDropRef.current) {
            suppressNextDropRef.current = false;
            return curr;
          }
          setEdges((prev) => withHeaderClamp(recomputeEdgeHandles(prev, next, changedIds), next));
          return decorateStatuses(next, edges);
        }

        let guardedNodes: Node[] = [];
        setEdges((eds) => {
          guardedNodes = guardHeaderAndMaybeGrow(next, eds);
          return withHeaderClamp(recomputeEdgeHandles(eds, guardedNodes), guardedNodes);
        });
        return decorateStatuses(guardedNodes, edges);
      });
    },
    [edges, decorateStatuses, guardHeaderAndMaybeGrow, withHeaderClamp, recomputeEdgeHandles],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) =>
      setEdges((eds) =>
        withHeaderClamp(
          decorateEdgeStatuses(applyEdgeChanges(changes, eds)),
          latestNodesRef.current,
        ),
      ),
    [decorateEdgeStatuses, withHeaderClamp],
  );

  const onNodeDragStop = useCallback(
    (_event: React.MouseEvent) => {
      suppressNextDropRef.current = true;
      setTimeout(() => (suppressNextDropRef.current = false), 0);

      let snapshot: Node[] | null = null;
      setNodes((nds) => {
        const tightened = fitRootTightly(nds, edges);
        snapshot = tightened;
        const ids = tightened.filter((n) => n.type !== "rootNode").map((n) => n.id);
        setTimeout(() => ids.forEach((id) => updateNodeInternals(id)), 0);
        setEdges((prev) => withHeaderClamp(recomputeEdgeHandles(prev, tightened), tightened));
        return tightened;
      });

      // Clear last dragging id after adjustments
      lastDraggingIdRef.current = null;

      const snap = snapshot as Node[] | null;
      if (snap && snap.length > 0) savePositionsSnapshot(snap);
      else savePositionsFromGraph();
      saveViewport();

      if (autoFitAfterDrag) {
        setTimeout(() => {
          setEdges((prev) => withHeaderClamp(prev, latestNodesRef.current));
          tightenAndFitWhenReady(withHeaderClamp(edges, latestNodesRef.current), {
            adjustPositions: false,
          }).catch(console.error);
        }, 0);
      }
    },
    [
      edges,
      fitRootTightly,
      updateNodeInternals,
      tightenAndFitWhenReady,
      autoFitAfterDrag,
      savePositionsFromGraph,
      savePositionsSnapshot,
      saveViewport,
      withHeaderClamp,
      recomputeEdgeHandles,
    ],
  );

  // Persist viewport when panning/zooming stops
  const onMoveEnd = useCallback(
    (_: any, vp: Viewport) => {
      if (vp) setViewportState(vp);
      saveViewport(vp);
    },
    [saveViewport],
  );

  const onViewportChange = useCallback((vp: Viewport) => {
    setViewportState(vp);
  }, []);

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
