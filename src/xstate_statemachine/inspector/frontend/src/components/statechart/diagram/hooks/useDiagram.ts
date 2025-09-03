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
import type { MachineState } from "@/store/slices/machineSlice";
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

  // Debug logging for node state changes
  useEffect(() => {
    console.debug("[useDiagram] nodes state changed:", {
      nodeCount: nodes.length,
      nodeIds: nodes.map((n) => n.id),
      timestamp: Date.now(),
    });
  }, [nodes]);

  useEffect(() => {
    console.debug("[useDiagram] edges state changed:", {
      edgeCount: edges.length,
      edgeIds: edges.map((e) => e.id),
      timestamp: Date.now(),
    });
  }, [edges]);

  const latestNodesRef = useRef<Node[]>([]);
  useEffect(() => {
    latestNodesRef.current = nodes;
  }, [nodes]);

  const suppressNextDropRef = useRef(false);

  const { fitView, getNodes, getViewport } = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();

  const storageKey = useMemo(() => `xsi.positions.${machine.id}`, [machine.id]);
  const viewportKey = useMemo(() => `xsi.viewport.${machine.id}`, [machine.id]);

  // Track machine definition changes to clear invalid saved positions
  const machineDefinitionRef = useRef(machine.definition);
  useEffect(() => {
    const currentDefinition = machine.definition;
    const previousDefinition = machineDefinitionRef.current;

    if (
      previousDefinition &&
      currentDefinition &&
      JSON.stringify(previousDefinition) !== JSON.stringify(currentDefinition)
    ) {
      console.debug("[useDiagram] machine definition changed, clearing saved positions");
      try {
        localStorage.removeItem(storageKey);
        localStorage.removeItem(viewportKey);
        setHasSavedPositions(false);
      } catch (error) {
        console.error("[useDiagram] failed to clear saved positions on definition change:", error);
      }
    }

    machineDefinitionRef.current = currentDefinition;
  }, [machine.definition, storageKey, viewportKey]);

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

        // 3) Positions: respect saved positions if present and valid
        const savedPositions = opts?.resetSavedPositions ? new Map() : loadSavedPositions();
        const hasSaved = savedPositions.size > 0;
        setHasSavedPositions(hasSaved);

        let positioned = withStatus;
        if (hasSaved) {
          // Only apply saved positions if they match the current node structure
          const currentNodeIds = new Set(withStatus.map((n) => n.id));
          const savedNodeIds = new Set(savedPositions.keys());
          const isValidStructure =
            currentNodeIds.size === savedNodeIds.size &&
            Array.from(currentNodeIds).every((id) => savedNodeIds.has(id));

          if (isValidStructure) {
            positioned = applySavedPositions(withStatus);
            console.debug("[useDiagram.relayout] applied saved positions");
          } else {
            console.debug("[useDiagram.relayout] saved positions invalid, using layout positions");
            setHasSavedPositions(false);
          }
        }

        const nextNodes =
          hasSaved && positioned !== withStatus
            ? positioned
            : guardHeaderAndMaybeGrow(positioned, edgesWithStatus);
        const nextEdges = withHeaderClamp(edgesWithStatus, nextNodes);

        console.debug("[useDiagram.relayout] before set state", {
          nextNodeCount: nextNodes.length,
          nextEdgeCount: nextEdges.length,
          nextNodeIds: nextNodes.map((n) => n.id),
          nextEdgeIds: nextEdges.map((e) => e.id),
          timestamp: Date.now(),
        });
        setEdges(nextEdges);
        setNodes(nextNodes);
        console.debug("[useDiagram.relayout] after set state", {
          timestamp: Date.now(),
        });

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
    console.debug("[useDiagram] re-decorating for activeStateIds change", {
      activeStateIds,
      timestamp: Date.now(),
    });
    setEdges((prev) => {
      const decorated = decorateEdgeStatuses(prev);
      console.debug("[useDiagram] edges re-decorated", {
        edgeCount: decorated.length,
        timestamp: Date.now(),
      });
      return decorated;
    });
    setNodes((prev) => {
      const decorated = decorateStatuses(prev, edges);
      console.debug("[useDiagram] nodes re-decorated", {
        nodeCount: decorated.length,
        nodeIds: decorated.map((n) => n.id),
        timestamp: Date.now(),
      });
      return decorated;
    });
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

      const dragging = changes.some((c) => c.type === "position" && c.dragging);

      setNodes((curr) => {
        console.debug("[useDiagram.onNodesChange] before applyNodeChanges", {
          currentCount: curr.length,
          currentIds: curr.map((n) => n.id),
          changeCount: changes.length,
          changes: changes.map((c) => ({ type: c.type, id: "id" in c ? c.id : "unknown" })),
          timestamp: Date.now(),
        });

        const next = applyNodeChanges(changes, curr);

        console.debug("[useDiagram.onNodesChange] after applyNodeChanges", {
          changeCount: changes.length,
          dragging,
          isDrop,
          draggingIds: Array.from(draggingIds),
          nextCount: next.length,
          nextIds: next.map((n) => n.id),
          timestamp: Date.now(),
        });

        if (dragging) {
          // During dragging, ensure parentId relationships are maintained
          const parented = ensureUnderRoot(next);
          console.debug("[useDiagram.onNodesChange] dragging - ensured under root", {
            parentedCount: parented.length,
            parentedIds: parented.map((n) => n.id),
            timestamp: Date.now(),
          });

          // Apply guard and grow logic
          const guarded = guardHeaderAndMaybeGrow(parented, edges, draggingIds);
          console.debug("[useDiagram.onNodesChange] dragging - guarded", {
            guardedCount: guarded.length,
            guardedIds: guarded.map((n) => n.id),
            timestamp: Date.now(),
          });

          // Update edges in a separate effect to avoid nested state updates
          setTimeout(() => {
            console.debug("[useDiagram.onNodesChange] dragging - updating edges", {
              timestamp: Date.now(),
            });
            setEdges((eds) => {
              const recomputed = recomputeEdgeHandles(eds, guarded, draggingIds);
              const clamped = withHeaderClamp(recomputed, guarded);
              console.debug("[useDiagram.onNodesChange] dragging - edges updated", {
                edgeCount: clamped.length,
                timestamp: Date.now(),
              });
              return clamped;
            });
          }, 0);

          const decorated = decorateStatuses(guarded, edges);
          console.debug("[useDiagram.onNodesChange] dragging - returning decorated", {
            decoratedCount: decorated.length,
            decoratedIds: decorated.map((n) => n.id),
            timestamp: Date.now(),
          });
          return decorated;
        }

        if (isDrop) {
          if (suppressNextDropRef.current) {
            suppressNextDropRef.current = false;
            console.debug("[useDiagram.onNodesChange] drop suppressed", {
              timestamp: Date.now(),
            });
            return curr;
          }

          // Ensure parentId relationships are maintained after drop
          const parented = ensureUnderRoot(next);
          console.debug("[useDiagram.onNodesChange] drop - ensured under root", {
            parentedCount: parented.length,
            parentedIds: parented.map((n) => n.id),
            timestamp: Date.now(),
          });

          console.debug("[useDiagram.onNodesChange] processing drop", {
            nextCount: parented.length,
            nextIds: parented.map((n) => n.id),
            timestamp: Date.now(),
          });

          // Update edges in a separate effect to avoid nested state updates
          setTimeout(() => {
            console.debug("[useDiagram.onNodesChange] drop - updating edges", {
              timestamp: Date.now(),
            });
            setEdges((prev) => {
              const recomputed = recomputeEdgeHandles(prev, parented, changedIds);
              const clamped = withHeaderClamp(recomputed, parented);
              console.debug("[useDiagram.onNodesChange] drop - edges updated", {
                edgeCount: clamped.length,
                timestamp: Date.now(),
              });
              return clamped;
            });
          }, 0);

          const decorated = decorateStatuses(parented, edges);
          console.debug("[useDiagram.onNodesChange] drop - returning decorated", {
            decoratedCount: decorated.length,
            decoratedIds: decorated.map((n) => n.id),
            timestamp: Date.now(),
          });
          return decorated;
        }

        // For other changes, ensure parentId relationships and apply guard and grow logic
        const parented = ensureUnderRoot(next);
        console.debug("[useDiagram.onNodesChange] other changes - ensured under root", {
          parentedCount: parented.length,
          parentedIds: parented.map((n) => n.id),
          timestamp: Date.now(),
        });

        console.debug("[useDiagram.onNodesChange] other changes - applying guard", {
          nextCount: parented.length,
          nextIds: parented.map((n) => n.id),
          timestamp: Date.now(),
        });

        const guarded = guardHeaderAndMaybeGrow(parented, edges);

        console.debug("[useDiagram.onNodesChange] other changes - guarded", {
          guardedCount: guarded.length,
          guardedIds: guarded.map((n) => n.id),
          timestamp: Date.now(),
        });

        // Update edges in a separate effect to avoid nested state updates
        setTimeout(() => {
          console.debug("[useDiagram.onNodesChange] other changes - updating edges", {
            timestamp: Date.now(),
          });
          setEdges((eds) => {
            const recomputed = recomputeEdgeHandles(eds, guarded);
            const clamped = withHeaderClamp(recomputed, guarded);
            console.debug("[useDiagram.onNodesChange] other changes - edges updated", {
              edgeCount: clamped.length,
              timestamp: Date.now(),
            });
            return clamped;
          });
        }, 0);

        const decorated = decorateStatuses(guarded, edges);
        console.debug("[useDiagram.onNodesChange] other changes - returning decorated", {
          decoratedCount: decorated.length,
          decoratedIds: decorated.map((n) => n.id),
          timestamp: Date.now(),
        });
        return decorated;
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
      console.debug("[useDiagram.onNodeDragStop] start", {
        nodeId: node?.id,
        timestamp: Date.now(),
      });
      suppressNextDropRef.current = true;
      setTimeout(() => {
        suppressNextDropRef.current = false;
        console.debug("[useDiagram.onNodeDragStop] suppressNextDropRef reset", {
          timestamp: Date.now(),
        });
      }, 0);

      let snapshot: Node[] | null = null;
      setNodes((nds) => {
        console.debug("[useDiagram.onNodeDragStop] before tighten", {
          nodeCount: nds.length,
          nodeIds: nds.map((n) => n.id),
          timestamp: Date.now(),
        });
        const tightened = fitRootTightly(nds, edges);
        console.debug("[useDiagram.onNodeDragStop] after tighten", {
          nodeCount: tightened.length,
          nodeIds: tightened.map((n) => n.id),
          timestamp: Date.now(),
        });
        snapshot = tightened;

        // Update node internals and edges in separate effects to avoid nested state updates
        const ids = tightened.filter((n) => n.type !== "rootNode").map((n) => n.id);
        setTimeout(() => {
          console.debug("[useDiagram.onNodeDragStop] updating node internals and edges", {
            nodeIds: ids,
            timestamp: Date.now(),
          });
          ids.forEach((id) => updateNodeInternals(id));
          setEdges((prev) => {
            const recomputed = recomputeEdgeHandles(prev, tightened);
            const clamped = withHeaderClamp(recomputed, tightened);
            console.debug("[useDiagram.onNodeDragStop] edges updated in setTimeout", {
              edgeCount: clamped.length,
              timestamp: Date.now(),
            });
            return clamped;
          });
        }, 0);

        console.debug("[useDiagram.onNodeDragStop] returning tightened nodes", {
          nodeCount: tightened.length,
          nodeIds: tightened.map((n) => n.id),
          timestamp: Date.now(),
        });
        return tightened;
      });

      // Save positions after state update
      setTimeout(() => {
        const snap = snapshot as Node[] | null;
        if (snap && snap.length > 0) {
          console.debug("[useDiagram.onNodeDragStop] saving snapshot", {
            nodeCount: snap.length,
            nodeIds: snap.map((n) => n.id),
            timestamp: Date.now(),
          });
          savePositionsSnapshot(snap);
        } else {
          console.debug("[useDiagram.onNodeDragStop] saving from graph", {
            timestamp: Date.now(),
          });
          savePositionsFromGraph();
        }
        console.debug("[useDiagram.onNodeDragStop] saving viewport", {
          timestamp: Date.now(),
        });
        saveViewport();
      }, 0);

      if (autoFitAfterDrag) {
        setTimeout(() => {
          console.debug("[useDiagram.onNodeDragStop] autoFitAfterDrag start", {
            timestamp: Date.now(),
          });
          const currentNodes = latestNodesRef.current;
          if (currentNodes && currentNodes.length > 0) {
            console.debug("[useDiagram.onNodeDragStop] autoFitAfterDrag - processing nodes", {
              nodeCount: currentNodes.length,
              nodeIds: currentNodes.map((n) => n.id),
              timestamp: Date.now(),
            });
            setEdges((prev) => {
              const clamped = withHeaderClamp(prev, currentNodes);
              console.debug("[useDiagram.onNodeDragStop] autoFitAfterDrag - edges clamped", {
                edgeCount: clamped.length,
                timestamp: Date.now(),
              });
              return clamped;
            });
            tightenAndFitWhenReady(withHeaderClamp(edges, currentNodes), {
              adjustPositions: false,
            }).catch(console.error);
          } else {
            console.debug("[useDiagram.onNodeDragStop] autoFitAfterDrag - no current nodes", {
              timestamp: Date.now(),
            });
          }
        }, 100); // Slightly longer delay to ensure state updates are complete
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
