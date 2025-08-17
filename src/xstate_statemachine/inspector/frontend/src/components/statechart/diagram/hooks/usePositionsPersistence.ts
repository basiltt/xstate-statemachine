import { useCallback } from "react";
import type { Node } from "reactflow";

export function usePositionsPersistence(storageKey: string, getNodes: () => Node[]) {
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
        return { ...n, position: { x: s.x, y: s.y } } as Node;
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

  const savePositionsSnapshot = useCallback(
    (list: Node[]) => {
      try {
        const map: Record<string, { x: number; y: number }> = {};
        for (const n of list) map[n.id] = { x: n.position.x, y: n.position.y };
        localStorage.setItem(storageKey, JSON.stringify(map));
      } catch {
        // ignore
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
