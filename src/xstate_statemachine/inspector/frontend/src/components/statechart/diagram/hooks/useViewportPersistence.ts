//  src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/hooks/useViewportPersistence.ts
import { useCallback, useMemo, useState } from "react";
import type { Viewport } from "reactflow";

export function useViewportPersistence(
  viewportKey: string,
  getViewport?: () => Viewport | undefined,
) {
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

  const [viewport, setViewportState] = useState<Viewport | undefined>(initialViewport ?? undefined);

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

  return { initialViewport, viewport, setViewportState, loadSavedViewport, saveViewport };
}
