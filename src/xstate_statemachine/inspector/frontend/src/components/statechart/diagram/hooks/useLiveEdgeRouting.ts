import { useCallback } from "react";
import type { Edge, Node } from "reactflow";
import { defaultRouterConfig, getNodeBoxes, routeEdges } from "./router";

type Dir = "L" | "R" | "T" | "B";
const PORTS_PER_SIDE = defaultRouterConfig.portsPerSide;

/**
 * Live handle picking with small hysteresis (Rule 7),
 * then defers to router for actual waypoints.
 */
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

      // cost fallback with hysteresis bias
      const dxC = dcx - scx;
      const dyC = dcy - scy;
      const lateralX = Math.abs(dyC) * 0.6;
      const lateralY = Math.abs(dxC) * 0.6;
      const cost = {
        L: Math.max(0, dL - sR) + lateralX,
        R: Math.max(0, sL - dR) + lateralX,
        T: Math.max(0, dT - sB) + lateralY,
        B: Math.max(0, sT - dB) + lateralY,
      } as Record<Dir, number>;

      let best: Dir = "L";
      (["L", "R", "T", "B"] as Dir[]).forEach((d) => {
        if (cost[d] < cost[best]) best = d;
      });

      if (prevDir && cost[prevDir] <= cost[best] + 18) best = prevDir; // hysteresis

      const sh = best === "L" ? "r" : best === "R" ? "l" : best === "T" ? "b" : "t";
      return { sh, th: best, dir: best };
    },
    [],
  );

  const getBoxes = useCallback(getNodeBoxes, []);

  function distribute(
    edges: Edge[],
    boxes: Map<string, { x: number; y: number; w: number; h: number }>,
  ) {
    type Ref = { ei: number; side: string; isSource: boolean; key: number; existingIdx?: number };
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
      const scx = sb.x + sb.w / 2,
        scy = sb.y + sb.h / 2;
      const tcx = tb.x + tb.w / 2,
        tcy = tb.y + tb.h / 2;
      const sSide = (e.sourceHandle ?? "").charAt(0);
      const tSide = (e.targetHandle ?? "").charAt(0);
      const sIdx = Number.isFinite(Number((e.sourceHandle ?? "").slice(1)))
        ? Number((e.sourceHandle as string).slice(1))
        : undefined;
      const tIdx = Number.isFinite(Number((e.targetHandle ?? "").slice(1)))
        ? Number((e.targetHandle as string).slice(1))
        : undefined;
      if (sSide)
        add(e.source, sSide, true, {
          ei: i,
          side: sSide,
          isSource: true,
          key: sSide === "l" || sSide === "r" ? tcy : tcx,
          existingIdx: sIdx,
        });
      if (tSide)
        add(e.target, tSide, false, {
          ei: i,
          side: tSide,
          isSource: false,
          key: tSide === "L" || tSide === "R" ? scy : scx,
          existingIdx: tIdx,
        });
    }
    for (const [, list] of groups) {
      const used = new Set<number>();
      for (const r of list) if (r.existingIdx != null) used.add(r.existingIdx);
      const missing = list.filter((r) => r.existingIdx == null);
      missing.sort((a, b) => a.key - b.key);
      let next = 0;
      for (const r of missing) {
        while (used.has(next)) next++;
        const idx = Math.min(PORTS_PER_SIDE - 1, next);
        used.add(idx);
        const id = `${r.side}${idx}`;
        if (r.isSource) edges[r.ei].sourceHandle = id;
        else edges[r.ei].targetHandle = id;
        next++;
      }
    }
  }

  const recomputeEdgeHandles = useCallback(
    (eds: Edge[], nds: Node[], onlyIds?: Set<string>): Edge[] => {
      const boxes = getBoxes(nds);
      // Step 1: choose sides (handles) with hysteresis
      const next = eds.map((e) => {
        if (!boxes.has(e.source) || !boxes.has(e.target)) return e;
        if (onlyIds && !onlyIds.has(e.source) && !onlyIds.has(e.target)) return e;
        const src = boxes.get(e.source)!;
        const dst = boxes.get(e.target)!;
        const prevDir = (e.data as any)?.dir as Dir | undefined;
        const { sh, th, dir } = pickHandlesRuntime(src, dst, prevDir);

        // Keep if unchanged
        const same =
          (e.sourceHandle?.startsWith(sh) ?? false) &&
          (e.targetHandle?.startsWith(th) ?? false) &&
          prevDir === dir;

        if (same) return e;

        return {
          ...e,
          sourceHandle: e.sourceHandle?.length ? e.sourceHandle : sh,
          targetHandle: e.targetHandle?.length ? e.targetHandle : th,
          data: {
            ...(e.data ?? {}),
            dir,
            _lastSides: { s: e.sourceHandle || sh, t: e.targetHandle || th },
          },
        } as Edge;
      });

      // Step 2: spread slots along sides deterministically
      distribute(next, boxes);

      // Step 3: route waypoints (deterministic; Rule 2–6)
      const { edges: routed } = routeEdges(nds, next, defaultRouterConfig, onlyIds);

      // Preserve object identity when identical
      const out: Edge[] = new Array(routed.length);
      const eps = 0.01;
      for (let i = 0; i < routed.length; i++) {
        const r = routed[i] as Edge;
        const b = eds[i];
        const rwp = (r.data as any)?.waypoints as { x: number; y: number }[] | undefined;
        const bwp = (b?.data as any)?.waypoints as { x: number; y: number }[] | undefined;
        const sameWP =
          Array.isArray(rwp) &&
          Array.isArray(bwp) &&
          rwp.length === bwp.length &&
          rwp.every((p, j) => Math.abs(p.x - bwp[j].x) < eps && Math.abs(p.y - bwp[j].y) < eps);
        if (
          b &&
          r.source === b.source &&
          r.target === b.target &&
          r.sourceHandle === b.sourceHandle &&
          r.targetHandle === b.targetHandle &&
          sameWP
        )
          out[i] = b;
        else out[i] = r;
      }
      return out;
    },
    [getBoxes, pickHandlesRuntime],
  );

  return { pickHandlesRuntime, getNodeBoxes: getBoxes, recomputeEdgeHandles };
}
