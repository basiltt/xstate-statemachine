//  src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/hooks/useViewportPersistence.ts
import { useCallback, useMemo, useState } from "react";
import type { Viewport } from "reactflow";

const MAX_OFFSET = 10000;

function parseViewport(raw: string | null): Viewport | null {
  if (!raw) return null;
  try {
    const vp = JSON.parse(raw) as any;
    if (
      vp &&
      typeof vp.x === "number" &&
      typeof vp.y === "number" &&
      typeof vp.zoom === "number" &&
      isFinite(vp.x) &&
      isFinite(vp.y) &&
      isFinite(vp.zoom) &&
      Math.abs(vp.x) <= MAX_OFFSET &&
      Math.abs(vp.y) <= MAX_OFFSET &&
      vp.zoom > 0 &&
      vp.zoom < 5
    ) {
      return vp as Viewport;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function useViewportPersistence(
  viewportKey: string,
  getViewport?: () => Viewport | undefined,
) {
  const initialViewport = useMemo<Viewport | null>(
    () => parseViewport(localStorage.getItem(viewportKey)),
    [viewportKey],
  );

  const [viewport, setViewportState] = useState<Viewport | undefined>(initialViewport ?? undefined);

  const loadSavedViewport = useCallback(
    (): Viewport | null => parseViewport(localStorage.getItem(viewportKey)),
    [viewportKey],
  );

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

  return { initialViewport, viewport, setViewportState, loadSavedViewport, saveViewport };
}
