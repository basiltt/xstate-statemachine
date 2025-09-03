import { useCallback, useMemo } from "react";
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
    (allNodes: Node[], eds: Edge[], draggingNodeIds: Set<string> = new Set()) => {
      const root = allNodes.find((n) => n.type === "rootNode");
      if (!root) return null;
      const children = allNodes.filter((n) => n.parentId === root.id && !draggingNodeIds.has(n.id));
      if (!children.length) return null;

      let minX = Infinity,
        minY = Infinity,
        maxX = -Infinity,
        maxY = -Infinity;

      let fallbackCount = 0;
      for (const ch of children) {
        let w = ch.width ?? 0;
        let h = ch.height ?? 0;
        if (!Number.isFinite(w) || w <= 0) {
          w = 120;
          fallbackCount++;
        }
        if (!Number.isFinite(h) || h <= 0) {
          h = 48;
          fallbackCount++;
        }
        minX = Math.min(minX, ch.position.x);
        minY = Math.min(minY, ch.position.y);
        maxX = Math.max(maxX, ch.position.x + w);
        maxY = Math.max(maxY, ch.position.y + h);
      }
      if (fallbackCount > 0) {
        console.warn("[useWrapperSizing.computeRootBounds] used fallback sizes for children", {
          fallbackCount,
        });
      }

      for (const e of eds) {
        const wps = (e.data as any)?.waypoints as { x: number; y: number }[] | undefined;
        if (Array.isArray(wps) && wps.length > 0) {
          for (const p of wps) {
            if (!Number.isFinite(p?.x) || !Number.isFinite(p?.y)) {
              console.warn("[useWrapperSizing.computeRootBounds] skipping non-finite waypoint", p);
              continue;
            }
            minX = Math.min(minX, p.x - EDGE_MARGIN);
            maxX = Math.max(maxX, p.x + EDGE_MARGIN);
            minY = Math.min(minY, p.y - EDGE_MARGIN);
            maxY = Math.max(maxY, p.y + EDGE_MARGIN);
          }
        }
      }

      if (
        !Number.isFinite(minX) ||
        !Number.isFinite(minY) ||
        !Number.isFinite(maxX) ||
        !Number.isFinite(maxY)
      ) {
        console.error("[useWrapperSizing.computeRootBounds] computed non-finite bounds, aborting", {
          minX,
          minY,
          maxX,
          maxY,
        });
        return null;
      }

      const minYForHeight = Math.max(minY, headerGuardTop);
      const width = Math.max(maxX - minX + PADDING, 320);
      const height = Math.max(maxY - minYForHeight + PADDING + reservedTop, reservedTop + 200);
      return { minX, minY, width, height };
    },
    [reservedTop, headerGuardTop],
  );

  const guardHeaderAndMaybeGrow = useCallback(
    (currentNodes: Node[], eds: Edge[], draggingIds: Set<string> = new Set()) => {
      console.log("[useWrapperSizing] guardHeaderAndMaybeGrow called:", {
        inputNodeCount: currentNodes.length,
        inputNodeIds: currentNodes.map((n) => n.id),
        edgeCount: eds.length,
      });

      const root = currentNodes.find((n) => n.type === "rootNode");
      const tight = computeRootBounds(currentNodes, eds, draggingIds);

      console.log("[useWrapperSizing] guardHeaderAndMaybeGrow - computed:", {
        hasRoot: !!root,
        rootId: root?.id,
        hasTight: !!tight,
        tight,
      });

      if (!root || !tight) {
        console.log("[useWrapperSizing] guardHeaderAndMaybeGrow - early return (no root or tight)");
        return currentNodes;
      }

      const desiredLeft = PADDING / 2;
      const desiredTop = headerGuardTop;

      let dx = tight.minX - desiredLeft;
      let dy = tight.minY - desiredTop;

      // Only move to enforce guards (no positive dx/dy which would create extra margin)
      dx = Math.min(dx, 0);
      dy = Math.min(dy, 0);

      if (Math.abs(dx) < 0.5) dx = 0;
      if (Math.abs(dy) < 0.5) dy = 0;

      if (
        !Number.isFinite(dx) ||
        !Number.isFinite(dy) ||
        Math.abs(dx) > 5000 ||
        Math.abs(dy) > 5000
      ) {
        console.warn(
          "[useWrapperSizing.guardHeaderAndMaybeGrow] suspicious translation; skipping",
          { dx, dy, tight, rootPos: root.position },
        );
        return currentNodes;
      }

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
          const newPos = { x: (n.position?.x ?? 0) + dx, y: (n.position?.y ?? 0) + dy };
          console.log("[useWrapperSizing] guardHeaderAndMaybeGrow - root move", {
            from: n.position,
            to: newPos,
            dx,
            dy,
            newWidth,
            newHeight,
          });
          return {
            ...n,
            position: newPos,
            style: { ...n.style, width: newWidth, height: newHeight },
          } as Node;
        }
        if (n.parentId === root.id) {
          const newPos = { x: n.position.x - dx, y: n.position.y - dy };
          console.log("[useWrapperSizing] guardHeaderAndMaybeGrow - child move", {
            id: n.id,
            from: n.position,
            to: newPos,
            dx,
            dy,
          });
          return { ...n, position: newPos } as Node;
        }
        return n;
      });
      console.log("[useWrapperSizing] guardHeaderAndMaybeGrow - final result:", {
        updatedNodeCount: updated.length,
        updatedNodeIds: updated.map((n) => n.id),
      });

      setTimeout(() => updateNodeInternals(root.id), 0);
      return updated;
    },
    [computeRootBounds, headerGuardTop, updateNodeInternals],
  );

  const fitRootTightly = useCallback(
    (currentNodes: Node[], eds: Edge[]) => {
      console.log("[useWrapperSizing] fitRootTightly called:", {
        inputNodeCount: currentNodes.length,
        inputNodeIds: currentNodes.map((n) => n.id),
        edgeCount: eds.length,
      });

      const root = currentNodes.find((n) => n.type === "rootNode");
      console.log("[useWrapperSizing] fitRootTightly - root found:", {
        hasRoot: !!root,
        rootId: root?.id,
      });

      const tight = computeRootBounds(currentNodes, eds, new Set());
      console.log("[useWrapperSizing] fitRootTightly - computed bounds:", {
        hasTight: !!tight,
        tight,
      });

      if (!root || !tight) {
        console.log("[useWrapperSizing] fitRootTightly - early return (no root or tight)");
        return currentNodes;
      }

      const desiredLeft = PADDING / 2;
      const desiredTop = headerGuardTop;
      let dx = tight.minX - desiredLeft;
      let dy = tight.minY - desiredTop;

      dx = Math.min(dx, 0);
      dy = Math.min(dy, 0);

      if (Math.abs(dx) < 0.5) dx = 0;
      if (Math.abs(dy) < 0.5) dy = 0;

      if (
        !Number.isFinite(dx) ||
        !Number.isFinite(dy) ||
        Math.abs(dx) > 5000 ||
        Math.abs(dy) > 5000
      ) {
        console.warn("[useWrapperSizing.fitRootTightly] suspicious translation; skipping", {
          dx,
          dy,
          tight,
          rootPos: root.position,
        });
        return currentNodes;
      }

      const currW: number | undefined = (root as any).width ?? (root.style as any)?.width;
      const currH: number | undefined = (root as any).height ?? (root.style as any)?.height;
      if (dx === 0 && dy === 0 && currW === tight.width && currH === tight.height) {
        return currentNodes;
      }

      const updated = currentNodes.map((n) => {
        if (n.id === root.id) {
          const newPos = { x: (n.position?.x ?? 0) + dx, y: (n.position?.y ?? 0) + dy };
          console.log("[useWrapperSizing] fitRootTightly - root move", {
            from: n.position,
            to: newPos,
            dx,
            dy,
            width: tight.width,
            height: tight.height,
          });
          return {
            ...n,
            position: newPos,
            style: { ...n.style, width: tight.width, height: tight.height },
          } as Node;
        }
        if (n.parentId === root.id) {
          const newPos = { x: n.position.x - dx, y: n.position.y - dy };
          console.log("[useWrapperSizing] fitRootTightly - child move", {
            id: n.id,
            from: n.position,
            to: newPos,
            dx,
            dy,
          });
          return { ...n, position: newPos } as Node;
        }
        return n;
      });

      console.log("[useWrapperSizing] fitRootTightly - after mapping:", {
        updatedNodeCount: updated.length,
        updatedNodeIds: updated.map((n) => n.id),
      });

      const sanitized = updated.map((n) => {
        const px = n.position?.x;
        const py = n.position?.y;
        if (!Number.isFinite(px) || !Number.isFinite(py)) {
          const fixed = {
            x: Number.isFinite(px) ? (px as number) : 0,
            y: Number.isFinite(py) ? (py as number) : 0,
          };
          console.warn("[useWrapperSizing] fitRootTightly - sanitized non-finite position", {
            id: n.id,
            from: n.position,
            to: fixed,
          });
          return { ...n, position: fixed } as Node;
        }
        return n;
      });

      console.log("[useWrapperSizing] fitRootTightly - final result:", {
        sanitizedNodeCount: sanitized.length,
        sanitizedNodeIds: sanitized.map((n) => n.id),
      });

      setTimeout(() => updateNodeInternals(root.id), 0);
      return sanitized;
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

  // Memoize clamp bounds to prevent frequent recalculations
  const clampBounds = useMemo(() => {
    return {
      reservedTop: params.reservedTop,
      inset: 22,
    };
  }, [params.reservedTop]);

  const withHeaderClamp = useCallback(
    (eds: Edge[], all: Node[]) => {
      const root = all.find((n) => n.type === "rootNode");
      if (!root) return eds;

      let width: number | undefined = (root as any).width ?? (root.style as any)?.width;
      let height: number | undefined = (root as any).height ?? (root.style as any)?.height;

      const topInner = (root.position?.y ?? 0) + clampBounds.reservedTop + 24;
      const leftInner = (root.position?.x ?? 0) + PADDING / 2 + clampBounds.inset;
      const rightInner =
        width != null
          ? (root.position?.x ?? 0) + width - PADDING / 2 - clampBounds.inset
          : Number.POSITIVE_INFINITY;
      const bottomInner =
        height != null
          ? (root.position?.y ?? 0) + height - PADDING / 2 - clampBounds.inset
          : Number.POSITIVE_INFINITY;

      // Use larger epsilon to prevent micro-oscillations
      const eps = 2.0;
      return eds.map((e) => {
        const d = (e.data ?? {}) as any;
        const same =
          Math.abs((d.clampTopY ?? NaN) - topInner) < eps &&
          Math.abs((d.clampLeftX ?? NaN) - leftInner) < eps &&
          Math.abs((d.clampRightX ?? NaN) - rightInner) < eps &&
          Math.abs((d.clampBottomY ?? NaN) - bottomInner) < eps;
        if (same) return e;

        // Round values to prevent floating point precision issues
        return {
          ...e,
          data: {
            ...(e.data ?? {}),
            clampTopY: Math.round(topInner * 10) / 10,
            clampLeftX: Math.round(leftInner * 10) / 10,
            clampRightX: Math.round(rightInner * 10) / 10,
            clampBottomY: Math.round(bottomInner * 10) / 10,
          },
        };
      });
    },
    [clampBounds],
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
