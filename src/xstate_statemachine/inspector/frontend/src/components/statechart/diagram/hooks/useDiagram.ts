import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { MachineState } from "@/hooks/useInspectorSocket";
import {
  EDGE_CLEAR_TOP,
  estimateReservedTop,
  headerGuardTop as calculateHeaderGuardTop,
  ROOT_HEADER,
} from "@/components/statechart/constants";
import { useViewportPersistence } from "@/components/statechart/diagram/hooks/useViewportPersistence.ts";
import { usePositionsPersistence } from "@/components/statechart/diagram/hooks/usePositionsPersistence.ts";
import { useStatusDecorators } from "@/components/statechart/diagram/hooks/useStatusDecorators.ts";
import { useLiveEdgeRouting } from "@/components/statechart/diagram/hooks/useLiveEdgeRouting.ts";
import { useWrapperSizing } from "@/components/statechart/diagram/hooks/useWrapperSizing.ts";
import { defaultRouterConfig, routeEdges } from "@/components/statechart/diagram/hooks/router.ts";

type UseDiagramProps = {
  machine: MachineState;
  activeStateIds: string[];
  autoFitAfterDrag?: boolean;
};

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

  const suppressNextDropRef = useRef(false);

  const { fitView, getNodes, getViewport } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const storageKey = useMemo(() => `xsi.positions.${machine.id}`, [machine.id]);
  const viewportKey = useMemo(() => `xsi.viewport.${machine.id}`, [machine.id]);

  const reservedTop = useMemo(
    () =>
      Math.max(estimateReservedTop(machine.context) + EDGE_CLEAR_TOP, ROOT_HEADER + EDGE_CLEAR_TOP),
    [machine.context],
  );
  const headerGuardTop = useMemo(() => calculateHeaderGuardTop(reservedTop), [reservedTop]);

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
    reservedTop,
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
      try {
        console.log("[useDiagram] Relayout called with machine:", {
          id: machine.id,
          definition: machine.definition,
          context: machine.context,
          hasDefinition: !!machine.definition,
          hasStates: !!machine.definition?.states,
        });

        if (opts?.resetSavedPositions) {
          try {
            localStorage.removeItem(storageKey);
          } catch {}
          setHasSavedPositions(false);
        }

        // 1) Build nodes/edges from definition
        const base = await getLayoutedElements(machine.definition, machine.context);
        console.log("[useDiagram] Layout elements generated:", {
          nodeCount: base.nodes.length,
          edgeCount: base.edges.length,
          nodes: base.nodes.map((n) => ({ id: n.id, type: n.type })),
          edges: base.edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
        });
        // 2) Deterministic rectilinear routing (ports & waypoints)
        const routed = routeEdges(base.nodes, base.edges, defaultRouterConfig);
        const edgesWithStatus = decorateEdgeStatuses(routed.edges as Edge[]);
        const parented = ensureUnderRoot(base.nodes);
        const withStatus = decorateStatuses(parented, edgesWithStatus);

        // 3) Positions: respect saved positions if present
        const hasSaved = opts?.resetSavedPositions ? false : loadSavedPositions().size > 0;
        setHasSavedPositions(hasSaved);

        const positioned = hasSaved ? applySavedPositions(withStatus) : withStatus;
        const nextNodes = hasSaved
          ? positioned
          : guardHeaderAndMaybeGrow(positioned, edgesWithStatus);
        const nextEdges = withHeaderClamp(edgesWithStatus, nextNodes);

        console.debug("[useDiagram.relayout] before set state", {
          nextNodeCount: nextNodes.length,
          nextEdgeCount: nextEdges.length,
        });
        setEdges(nextEdges);
        setNodes(nextNodes);
        console.debug("[useDiagram.relayout] after set state");

        if (opts?.resetSavedPositions) savePositionsSnapshot(nextNodes);

        const savedVp = loadSavedViewport();
        if (initialViewport) setViewportState(initialViewport);
        else if (savedVp) setViewportState(savedVp);
        else tightenAndFitWhenReady(nextEdges, { adjustPositions: !hasSaved }).catch(console.error);
      } catch (err) {
        console.error("[relayout] failed, falling back:", err);
        // Fallback: show root wrapper so the canvas is never empty
        const machineId = machine.definition?.id ?? "StateMachine";
        const rootId = `${machineId}__root`;
        const fallbackNodes: Node[] = [
          {
            id: rootId,
            type: "rootNode",
            data: { label: machineId, context: machine.context ?? {} },
            position: { x: 16, y: 16 },
            style: { width: 980, height: 560 },
            draggable: true,
            selectable: false,
          },
        ];
        setNodes(fallbackNodes);
        setEdges([]);
      }
    },
    [
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
      withHeaderClamp,
      savePositionsSnapshot,
      storageKey,
    ],
  );

  useEffect(() => {
    relayout().catch(console.error);
  }, [relayout]);

  // Re-decorate active/next highlights without recomputing layout
  useEffect(() => {
    setEdges((prev) => decorateEdgeStatuses(prev));
    setNodes((prev) => decorateStatuses(prev, edges));
  }, [activeStateIds, decorateStatuses, decorateEdgeStatuses]);

  /* --------------------------- RF change handlers ------------------------- */
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      let isDrop = false;
      const draggingIds = new Set<string>();
      const changedIds = new Set<string>();
      for (const c of changes) {
        if (c.type === "position") {
          changedIds.add(c.id);
          if (c.dragging) draggingIds.add(c.id);
          else isDrop = true;
        }
      }

      setNodes((curr) => {
        const next = applyNodeChanges(changes, curr);
        const dragging = changes.some((c) => c.type === "position" && c.dragging);

        if (dragging) {
          let guarded: Node[] = [];
          setEdges((eds) => {
            guarded = guardHeaderAndMaybeGrow(next, eds, draggingIds);
            console.debug("[useDiagram.onNodesChange] dragging update", {
              draggingIds: Array.from(draggingIds),
              nextCount: next.length,
              guardedCount: guarded.length,
            });
            return withHeaderClamp(recomputeEdgeHandles(eds, guarded, draggingIds), guarded);
          });
          return decorateStatuses(guarded, edges);
        }

        if (isDrop) {
          if (suppressNextDropRef.current) {
            suppressNextDropRef.current = false;
            return curr;
          }
          setEdges((prev) => withHeaderClamp(recomputeEdgeHandles(prev, next, changedIds), next));
          return decorateStatuses(next, edges);
        }

        let guarded: Node[] = [];
        setEdges((eds) => {
          guarded = guardHeaderAndMaybeGrow(next, eds);
          return withHeaderClamp(recomputeEdgeHandles(eds, guarded), guarded);
        });
        return decorateStatuses(guarded, edges);
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
    (_: any, node: Node) => {
      console.debug("[useDiagram.onNodeDragStop] start", { nodeId: node?.id });
      suppressNextDropRef.current = true;
      setTimeout(() => (suppressNextDropRef.current = false), 0);

      let snapshot: Node[] | null = null;
      setNodes((nds) => {
        console.debug("[useDiagram.onNodeDragStop] before tighten", { nodeCount: nds.length });
        const tightened = fitRootTightly(nds, edges);
        console.debug("[useDiagram.onNodeDragStop] after tighten", { nodeCount: tightened.length });
        snapshot = tightened;
        const ids = tightened.filter((n) => n.type !== "rootNode").map((n) => n.id);
        setTimeout(() => ids.forEach((id) => updateNodeInternals(id)), 0);
        setEdges((prev) => withHeaderClamp(recomputeEdgeHandles(prev, tightened), tightened));
        return tightened;
      });

      const snap = snapshot as Node[] | null;
      if (snap && snap.length > 0) savePositionsSnapshot(snap);
      else savePositionsFromGraph();
      saveViewport();

      if (autoFitAfterDrag) {
        setTimeout(() => {
          console.debug("[useDiagram.onNodeDragStop] autoFitAfterDrag");
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
