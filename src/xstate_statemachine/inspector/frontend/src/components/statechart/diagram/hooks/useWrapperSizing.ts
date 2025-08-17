import { useCallback } from "react";
import type { Edge, Node, Viewport } from "reactflow";
import { EDGE_MARGIN, PADDING } from "@/components/statechart/constants";

const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

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

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          return {
            ...n,
            position: { x: (n.position?.x ?? 0) + dx, y: (n.position?.y ?? 0) + dy },
            style: { ...n.style, width: tight.width, height: tight.height },
          } as Node;
        }
        if (n.parentId === root.id) {
          return { ...n, position: { x: n.position.x - dx, y: n.position.y - dy } } as Node;
        }
        return n;
      });

      updateNodeInternals(root.id);
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

      updateNodeInternals(root.id);
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
        // Note: The caller must wrap a setNodes call around this function
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
      if (width == null || height == null) {
        const tight = computeRootBounds(all, eds);
        if (tight) {
          width ??= tight.width;
          height ??= tight.height;
        }
      }

      const inset = 28;
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

      return eds.map((e) => ({
        ...e,
        data: {
          ...(e.data ?? {}),
          clampTopY: topInner,
          clampLeftX: leftInner,
          clampRightX: rightInner,
          clampBottomY: bottomInner,
        },
      }));
    },
    [computeRootBounds, params.reservedTop],
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
