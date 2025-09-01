import { useCallback } from "react";
import type { Edge, Node, Viewport } from "reactflow";
import { EDGE_MARGIN, PADDING } from "@/components/statechart/constants";

const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

/**
 * Wrapper auto-size & header guard.
 * Includes edges (with waypoints) and grows when wires hit borders (Rule 8).
 */
export function useWrapperSizing(params: {
  reservedTop: number;
  headerGuardTop: number;
  fitView: (args: any) => void;
  getNodes: () => Node[];
  updateNodeInternals: (id: string) => void;
  saveViewport: (vp?: Viewport) => void;
  hasSavedPositions: boolean;
}) {
  const {
    reservedTop,
    headerGuardTop,
    fitView,
    getNodes,
    updateNodeInternals,
    saveViewport,
    hasSavedPositions,
  } = params;

  const ensureUnderRoot = useCallback((nds: Node[]): Node[] => {
    const root = nds.find((n) => n.type === "rootNode");
    if (!root) return nds;
    return nds.map((n) =>
      n.id === root.id
        ? n
        : {
            ...n,
            parentId: root.id,
            extent: "parent",
            draggable: true,
            expandParent: true,
          },
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

      for (const e of eds) {
        const wps = (e.data as any)?.waypoints as { x: number; y: number }[] | undefined;
        if (Array.isArray(wps) && wps.length > 0) {
          for (const p of wps) {
            minX = Math.min(minX, p.x - EDGE_MARGIN);
            maxX = Math.max(maxX, p.x + EDGE_MARGIN);
            minY = Math.min(minY, p.y - EDGE_MARGIN);
            maxY = Math.max(maxY, p.y + EDGE_MARGIN);
          }
        }
      }

      const minYForHeight = Math.max(minY, headerGuardTop);
      const width = Math.max(maxX - minX + PADDING, 320);
      const height = Math.max(maxY - minYForHeight + PADDING + reservedTop, reservedTop + 200);
      return { minX, minY, width, height };
    },
    [reservedTop, headerGuardTop],
  );

  const guardHeaderAndMaybeGrow = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!root || !tight) return currentNodes;

      const desiredLeft = PADDING / 2;
      const desiredTop = headerGuardTop;

      let dx = tight.minX - desiredLeft;
      let dy = tight.minY - desiredTop;

      if (Math.abs(dx) < 0.5) dx = 0;
      if (Math.abs(dy) < 0.5) dy = 0;

      const currW: number | undefined = (root as any).width ?? (root.style as any)?.width;
      const currH: number | undefined = (root as any).height ?? (root.style as any)?.height;

      // Expand when any waypoint touches the inner edge (Rule 8)
      let growLeft = 0,
        growRight = 0,
        growTop = 0,
        growBottom = 0;
      const clampInset = 22;
      const innerLeft = (root.position?.x ?? 0) + PADDING / 2 + clampInset;
      const innerTop = (root.position?.y ?? 0) + params.reservedTop + 24;
      const innerRight =
        currW != null ? (root.position?.x ?? 0) + currW - PADDING / 2 - clampInset : Infinity;
      const innerBottom =
        currH != null ? (root.position?.y ?? 0) + currH - PADDING / 2 - clampInset : Infinity;

      for (const e of eds) {
        const wps = (e.data as any)?.waypoints as { x: number; y: number }[] | undefined;
        if (!wps) continue;
        for (const p of wps) {
          if (p.x <= innerLeft) growLeft = Math.max(growLeft, 32);
          if (p.x >= innerRight) growRight = Math.max(growRight, 32);
          if (p.y <= innerTop) growTop = Math.max(growTop, 32);
          if (p.y >= innerBottom) growBottom = Math.max(growBottom, 32);
        }
      }

      const newWidth = Math.max(tight.width + growLeft + growRight, currW ?? 0);
      const newHeight = Math.max(tight.height + growTop + growBottom, currH ?? 0);

      if (dx === 0 && dy === 0 && currW === newWidth && currH === newHeight) {
        return currentNodes;
      }

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          return {
            ...n,
            position: { x: (n.position?.x ?? 0) + dx, y: (n.position?.y ?? 0) + dy },
            style: { ...n.style, width: newWidth, height: newHeight },
          } as Node;
        }
        if (n.parentId === root.id) {
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } } as Node;
        }
        return n;
      });
      setTimeout(() => updateNodeInternals(root.id), 0);
      return updated;
    },
    [computeRootBounds, headerGuardTop, updateNodeInternals],
  );

  const fitRootTightly = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds);
      if (!root || !tight) return currentNodes;

      const desiredLeft = PADDING / 2;
      const desiredTop = headerGuardTop;
      const dx = tight.minX - desiredLeft;
      const dy = tight.minY - desiredTop;

      const currW: number | undefined = (root as any).width ?? (root.style as any)?.width;
      const currH: number | undefined = (root as any).height ?? (root.style as any)?.height;
      if (dx === 0 && dy === 0 && currW === tight.width && currH === tight.height) {
        return currentNodes;
      }

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          return {
            ...n,
            position: { x: (n.position?.x ?? 0) + dx, y: (n.position?.y ?? 0) + dy },
            style: { ...n.style, width: tight.width, height: tight.height },
          } as Node;
        }
        if (n.parentId === root.id)
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } } as Node;
        return n;
      });
      setTimeout(() => updateNodeInternals(root.id), 0);
      return updated;
    },
    [computeRootBounds, headerGuardTop, updateNodeInternals],
  );

  const tightenAndFitWhenReady = useCallback(
    async (_eds: Edge[], opts?: { adjustPositions?: boolean }) => {
      await nextFrame();
      await nextFrame();

      const ids = getNodes()
        .filter((n) => n.type !== "rootNode")
        .map((n) => n.id);
      ids.forEach((id) => updateNodeInternals(id));

      await nextFrame();
      const shouldAdjust = opts?.adjustPositions ?? !hasSavedPositions;
      if (shouldAdjust) {
        // caller adjusts positions before fitting
      }

      fitView({ duration: 500, padding: 0.18, includeHiddenNodes: true });
      setTimeout(() => saveViewport(), 0);
    },
    [getNodes, updateNodeInternals, fitView, saveViewport, hasSavedPositions],
  );

  const withHeaderClamp = useCallback(
    (eds: Edge[], all: Node[]) => {
      const root = all.find((n) => n.type === "rootNode");
      if (!root) return eds;

      let width: number | undefined = (root as any).width ?? (root.style as any)?.width;
      let height: number | undefined = (root as any).height ?? (root.style as any)?.height;

      const inset = 22; // consistent with edges renderer
      const topInner = (root.position?.y ?? 0) + params.reservedTop + 24;
      const leftInner = (root.position?.x ?? 0) + PADDING / 2 + inset;
      const rightInner =
        width != null
          ? (root.position?.x ?? 0) + width - PADDING / 2 - inset
          : Number.POSITIVE_INFINITY;
      const bottomInner =
        height != null
          ? (root.position?.y ?? 0) + height - PADDING / 2 - inset
          : Number.POSITIVE_INFINITY;

      const eps = 0.5;
      return eds.map((e) => {
        const d = (e.data ?? {}) as any;
        const same =
          Math.abs((d.clampTopY ?? NaN) - topInner) < eps &&
          Math.abs((d.clampLeftX ?? NaN) - leftInner) < eps &&
          Math.abs((d.clampRightX ?? NaN) - rightInner) < eps &&
          Math.abs((d.clampBottomY ?? NaN) - bottomInner) < eps;
        if (same) return e;
        return {
          ...e,
          data: {
            ...(e.data ?? {}),
            clampTopY: topInner,
            clampLeftX: leftInner,
            clampRightX: rightInner,
            clampBottomY: bottomInner,
          },
        };
      });
    },
    [params.reservedTop],
  );

  return {
    ensureUnderRoot,
    computeRootBounds,
    guardHeaderAndMaybeGrow,
    fitRootTightly,
    tightenAndFitWhenReady,
    withHeaderClamp,
  };
}
