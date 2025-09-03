//  src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/hooks/usePositionsPersistence.ts
import { useCallback } from "react";
import type { Node } from "reactflow";

export function usePositionsPersistence(storageKey: string, getNodes: () => Node[]) {
  const loadSavedPositions = useCallback((): Map<string, { x: number; y: number }> => {
    try {
      const raw = localStorage.getItem(storageKey);
      console.log("[usePositionsPersistence] loadSavedPositions:", {
        storageKey,
        hasRaw: !!raw,
        rawLength: raw?.length || 0,
      });
      if (!raw) return new Map();
      const obj = JSON.parse(raw) as Record<string, { x: number; y: number }>;
      const result = new Map(Object.entries(obj));
      console.log("[usePositionsPersistence] loaded positions:", {
        count: result.size,
        positions: Array.from(result.entries()),
      });
      return result;
    } catch (error) {
      console.error("[usePositionsPersistence] loadSavedPositions error:", error);
      return new Map();
    }
  }, [storageKey]);

  const applySavedPositions = useCallback(
    (list: Node[]): Node[] => {
      const saved = loadSavedPositions();
      console.log("[usePositionsPersistence] applySavedPositions:", {
        inputNodeCount: list.length,
        savedPositionsCount: saved.size,
        nodeIds: list.map((n) => n.id),
      });
      if (saved.size === 0) return list;

      // Validate that saved positions match current node structure
      const currentNodeIds = new Set(list.map((n) => n.id));
      const savedNodeIds = new Set(saved.keys());
      const hasStructuralChanges =
        currentNodeIds.size !== savedNodeIds.size ||
        !Array.from(currentNodeIds).every((id) => savedNodeIds.has(id));

      if (hasStructuralChanges) {
        console.log(
          "[usePositionsPersistence] structural changes detected, clearing saved positions:",
          {
            currentNodes: Array.from(currentNodeIds),
            savedNodes: Array.from(savedNodeIds),
          },
        );
        // Clear invalid saved positions
        try {
          localStorage.removeItem(storageKey);
        } catch (error) {
          console.error("[usePositionsPersistence] failed to clear invalid positions:", error);
        }
        return list;
      }

      const result = list.map((n) => {
        const s = saved.get(n.id);
        if (!s) {
          console.log("[usePositionsPersistence] no saved position for node:", n.id);
          return n;
        }

        // Validate position values
        if (
          typeof s.x !== "number" ||
          typeof s.y !== "number" ||
          !isFinite(s.x) ||
          !isFinite(s.y)
        ) {
          console.log("[usePositionsPersistence] invalid saved position for node:", n.id, s);
          return n;
        }

        console.log("[usePositionsPersistence] applying saved position:", {
          nodeId: n.id,
          oldPosition: n.position,
          newPosition: s,
        });
        return { ...n, position: { x: s.x, y: s.y } } as Node;
      });
      console.log("[usePositionsPersistence] applySavedPositions result:", {
        outputNodeCount: result.length,
      });
      return result;
    },
    [loadSavedPositions, storageKey],
  );

  const savePositionsFromGraph = useCallback(() => {
    try {
      const nodes = getNodes();
      const map: Record<string, { x: number; y: number }> = {};
      for (const n of nodes) {
        map[n.id] = { x: n.position.x, y: n.position.y };
      }
      console.log("[usePositionsPersistence] savePositionsFromGraph:", {
        nodeCount: nodes.length,
        positions: Object.entries(map),
      });
      localStorage.setItem(storageKey, JSON.stringify(map));
    } catch (error) {
      console.error("[usePositionsPersistence] savePositionsFromGraph error:", error);
    }
  }, [getNodes, storageKey]);

  const savePositionsSnapshot = useCallback(
    (list: Node[]) => {
      try {
        const map: Record<string, { x: number; y: number }> = {};
        for (const n of list) map[n.id] = { x: n.position.x, y: n.position.y };
        console.log("[usePositionsPersistence] savePositionsSnapshot:", {
          nodeCount: list.length,
          positions: Object.entries(map),
        });
        localStorage.setItem(storageKey, JSON.stringify(map));
      } catch (error) {
        console.error("[usePositionsPersistence] savePositionsSnapshot error:", error);
      }
    },
    [storageKey],
  );

  return {
    loadSavedPositions,
    applySavedPositions,
    savePositionsFromGraph,
    savePositionsSnapshot,
  };
}
