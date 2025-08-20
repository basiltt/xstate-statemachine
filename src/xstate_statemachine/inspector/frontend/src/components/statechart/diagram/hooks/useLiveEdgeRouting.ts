import { useCallback } from "react";
import type { Edge, Node } from "reactflow";
import { defaultRouterConfig, routeEdges } from "./router";

export type Dir = "L" | "R" | "T" | "B";
const PORTS_PER_SIDE = 24;

export function useLiveEdgeRouting() {
  const pickHandlesRuntime = useCallback(
    (
      src: { x: number; y: number; w: number; h: number },
      dst: { x: number; y: number; w: number; h: number },
      prevDir?: Dir,
    ): { sh: string; th: string; dir: Dir } => {
      const sL = src.x,
        sT = src.y,
        sR = src.x + src.w,
        sB = src.y + src.h;
      const dL = dst.x,
        dT = dst.y,
        dR = dst.x + dst.w,
        dB = dst.y + dst.h;
      const scx = sL + src.w / 2,
        scy = sT + src.h / 2;
      const dcx = dL + dst.w / 2,
        dcy = dT + dst.h / 2;

      const vBandTop = dT + Math.min(24, dst.h * 0.35);
      const vBandBot = dB - Math.min(24, dst.h * 0.35);
      const inVerticalBand = scy >= vBandTop && scy <= vBandBot;

      const hBandLeft = dL + Math.min(36, dst.w * 0.35);
      const hBandRight = dR - Math.min(36, dst.w * 0.35);
      const inHorizontalBand = scx >= hBandLeft && scx <= hBandRight;

      if (inVerticalBand) {
        const dir: Dir = scx < dL ? "L" : scx > dR ? "R" : (prevDir ?? (dcx >= scx ? "L" : "R"));
        const sh = dir === "L" ? "r" : "l";
        return { sh, th: dir, dir };
      }
      if (inHorizontalBand) {
        const dir: Dir = scy < dT ? "T" : scy > dB ? "B" : (prevDir ?? (dcy >= scy ? "T" : "B"));
        const sh = dir === "T" ? "b" : "t";
        return { sh, th: dir, dir };
      }

      const dxC = dcx - scx;
      const dyC = dcy - scy;
      const lateralX = Math.abs(dyC) * 0.6;
      const lateralY = Math.abs(dxC) * 0.6;
      const costToLeft = Math.max(0, dL - sR) + lateralX;
      const costToRight = Math.max(0, sL - dR) + lateralX;
      const costToTop = Math.max(0, dT - sB) + lateralY;
      const costToBottom = Math.max(0, sT - dB) + lateralY;

      const candidates: Array<{ dir: Dir; sh: string; th: string; cost: number }> = [
        { dir: "L", sh: "r", th: "L", cost: costToLeft },
        { dir: "R", sh: "l", th: "R", cost: costToRight },
        { dir: "T", sh: "b", th: "T", cost: costToTop },
        { dir: "B", sh: "t", th: "B", cost: costToBottom },
      ];
      let best = candidates[0];
      for (const c of candidates) if (c.cost < best.cost) best = c;

      if (prevDir) {
        const prev = candidates.find((c) => c.dir === prevDir)!;
        const eps = 18;
        if (prev && prev.cost <= best.cost + eps) best = prev;
      }
      return { sh: best.sh, th: best.th, dir: best.dir };
    },
    [],
  );

  const getNodeBoxes = useCallback((all: Node[]) => {
    const map = new Map<string, { x: number; y: number; w: number; h: number }>();
    for (const n of all) {
      const w = (n.width ?? (n.style as any)?.width ?? 160) as number;
      const h = (n.height ??
        (n.style as any)?.height ??
        (n.type === "eventNode" ? 36 : 120)) as number;
      map.set(n.id, { x: n.position.x, y: n.position.y, w, h });
    }
    return map;
  }, []);

  // Assign indices per side for multiple edges, stable by projection of the counterpart
  function distribute(
    edges: Edge[],
    boxes: Map<string, { x: number; y: number; w: number; h: number }>,
  ) {
    type Ref = { ei: number; side: string; isSource: boolean; key: number };
    const groups = new Map<string, Ref[]>();
    const add = (nodeId: string, side: string, isSource: boolean, ref: Ref) => {
      const k = `${nodeId}|${side}|${isSource ? "S" : "T"}`;
      (groups.get(k) || groups.set(k, []).get(k)!).push(ref);
    };
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      const sb = boxes.get(e.source);
      const tb = boxes.get(e.target);
      if (!sb || !tb) continue;
      const scx = sb.x + sb.w / 2;
      const scy = sb.y + sb.h / 2;
      const tcx = tb.x + tb.w / 2;
      const tcy = tb.y + tb.h / 2;
      const sSide = (e.sourceHandle ?? "").charAt(0);
      const tSide = (e.targetHandle ?? "").charAt(0);
      if (sSide)
        add(e.source, sSide, true, {
          ei: i,
          side: sSide,
          isSource: true,
          key: sSide === "l" || sSide === "r" ? tcy : tcx,
        });
      if (tSide)
        add(e.target, tSide, false, {
          ei: i,
          side: tSide,
          isSource: false,
          key: tSide === "L" || tSide === "R" ? scy : scx,
        });
    }
    for (const [, list] of groups) {
      list.sort((a, b) => a.key - b.key);
      for (let idx = 0; idx < list.length; idx++) {
        const ref = list[idx];
        const id = `${ref.side}${Math.min(PORTS_PER_SIDE - 1, idx)}`;
        if (ref.isSource) edges[ref.ei].sourceHandle = id;
        else edges[ref.ei].targetHandle = id;
      }
    }
  }

  const recomputeEdgeHandles = useCallback(
    (eds: Edge[], nds: Node[], onlyIds?: Set<string>): Edge[] => {
      const boxes = getNodeBoxes(nds);
      let changed = false;
      const next = eds.map((e) => {
        if (!boxes.has(e.source) || !boxes.has(e.target)) return e;
        if (onlyIds && !onlyIds.has(e.source) && !onlyIds.has(e.target)) return e;
        const src = boxes.get(e.source)!;
        const dst = boxes.get(e.target)!;
        const prevDir = (e.data as any)?.dir as Dir | undefined;
        const { sh, th, dir } = pickHandlesRuntime(src, dst, prevDir);
        const same =
          e.sourceHandle?.startsWith(sh) && e.targetHandle?.startsWith(th) && prevDir === dir;
        if (same) return e;
        changed = true;
        return {
          ...e,
          sourceHandle: sh,
          targetHandle: th,
          data: { ...(e.data ?? {}), dir },
        } as Edge;
      });

      // distribute multiple edges per side with numbered ports
      distribute(next, boxes);
      // Route orthogonal waypoints using the deterministic router
      const { edges: routed } = routeEdges(nds, next, defaultRouterConfig, onlyIds);
      return changed ? (routed as Edge[]) : (routed as Edge[]);
    },
    [getNodeBoxes, pickHandlesRuntime],
  );

  return { pickHandlesRuntime, getNodeBoxes, recomputeEdgeHandles };
}
