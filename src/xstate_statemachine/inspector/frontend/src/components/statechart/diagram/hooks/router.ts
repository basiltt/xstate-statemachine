/**
 * Deterministic rectilinear router with side/slot selection (Rule 1),
 * fast path (Rule 2), A* fallback (Rule 3), corridor & crossings (Rule 4),
 * multi-edge separation (Rule 6), incremental updates (Rule 7), and diagnostics (Rule 14).
 */

import type { Edge, Node } from "reactflow";
import RBush from "rbush";

/* ───────────────────────── Types & config ───────────────────────── */

export type PortSide = "l" | "r" | "t" | "b" | "L" | "R" | "T" | "B";
type XY = { x: number; y: number };

export type RouterConfig = {
  node_margin: number;
  wire_gap: number;
  egress_len: number;
  min_egress: number;
  corner_radius: number;
  G: number;
  P: number;
  edge_padding: number;
  grow_step?: number;
  min_wrapper_w?: number;
  min_wrapper_h?: number;

  // weights
  weights: {
    alpha: number; // bends
    beta: number; // crowding
    gamma: number; // crossing_penalty
    delta: number; // side_change_penalty
    bend_weight: number; // A* turn cost
  };

  portsPerSide: number;
  maxAStarExpansions: number;
};

export type RoutedEdge = Edge & {
  data?: Edge["data"] & {
    waypoints?: XY[];
    sourcePort?: { side: string; slot: number };
    targetPort?: { side: string; slot: number };
    laneOffset?: number;
    cornerR?: number;
    // remember last chosen sides for hysteresis
    _lastSides?: { s: string; t: string };
  };
};

export type RouterDiagnostics = { crossings: number; avg_bends: number; reroutedCount: number };

/* ───────────────────────── Helpers ───────────────────────── */

const keySS = (nodeId: string, side: PortSide) => `${nodeId}|${side}`;

const manhattan = (a: XY, b: XY) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
const snapTo = (v: number, G: number) => Math.round(v / G) * G;

const sideNormal = (s: PortSide): XY =>
  s.toLowerCase() === "l"
    ? { x: -1, y: 0 }
    : s.toLowerCase() === "r"
      ? { x: 1, y: 0 }
      : s.toLowerCase() === "t"
        ? { x: 0, y: -1 }
        : { x: 0, y: 1 };

const dot = (a: XY, b: XY) => a.x * b.x + a.y * b.y;

function center(b: { x: number; y: number; w: number; h: number }) {
  return { x: b.x + b.w / 2, y: b.y + b.h / 2 };
}

function inflate(b: { x: number; y: number; w: number; h: number }, m: number) {
  return { x: b.x - m, y: b.y - m, w: b.w + 2 * m, h: b.h + 2 * m };
}

function rectIntersectsSegment(
  rect: { x: number; y: number; w: number; h: number },
  a: XY,
  b: XY,
): boolean {
  // horizontal/vertical only
  const minX = Math.min(a.x, b.x);
  const maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const maxY = Math.max(a.y, b.y);
  const r = rect;
  if (maxX < r.x || minX > r.x + r.w || maxY < r.y || minY > r.y + r.h) return false;
  if (a.y === b.y) {
    const y = a.y;
    return y >= r.y && y <= r.y + r.h && !(maxX < r.x || minX > r.x + r.w);
  } else {
    const x = a.x;
    return x >= r.x && x <= r.x + r.w && !(maxY < r.y || minY > r.y + r.h);
  }
}

function segmentBBox(a: XY, b: XY, pad: number) {
  const minX = Math.min(a.x, b.x) - pad;
  const maxX = Math.max(a.x, b.x) + pad;
  const minY = Math.min(a.y, b.y) - pad;
  const maxY = Math.max(a.y, b.y) + pad;
  return { minX, minY, maxX, maxY };
}

function compress(points: XY[]): XY[] {
  const out: XY[] = [];
  for (const p of points) {
    const n = out.length;
    if (n >= 2) {
      const a = out[n - 2];
      const b = out[n - 1];
      if ((a.x === b.x && b.x === p.x) || (a.y === b.y && b.y === p.y)) {
        out[n - 1] = p;
        continue;
      }
    }
    out.push(p);
  }
  return out;
}

function portPoint(
  box: { x: number; y: number; w: number; h: number },
  side: PortSide,
  slot: number,
  portsPerSide: number,
  egress: number,
): XY {
  const frac = (slot + 1) / (portsPerSide + 1);
  switch (side) {
    case "l":
    case "L":
      return { x: box.x - egress, y: box.y + box.h * frac };
    case "r":
    case "R":
      return { x: box.x + box.w + egress, y: box.y + box.h * frac };
    case "t":
    case "T":
      return { x: box.x + box.w * frac, y: box.y - egress };
    case "b":
    case "B":
      return { x: box.x + box.w * frac, y: box.y + box.h + egress };
  }
}

/* ───────────────────────── Spatial index (R-tree) ───────────────────────── */

type BoxItem = { minX: number; minY: number; maxX: number; maxY: number; kind: "node" | "edge" };

function corridorBoxes(pts: XY[], wireGap: number): BoxItem[] {
  const pad = Math.max(2, Math.floor(wireGap / 2));
  const items: BoxItem[] = [];
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1];
    const b = pts[i];
    const bb = segmentBBox(a, b, pad);
    items.push({ ...bb, kind: "edge" });
  }
  return items;
}

/* ───────────────────────── A* grid router (with soft corridor costs) ───────────────────────── */

function astar(
  start: XY,
  end: XY,
  obstacleRects: { x: number; y: number; w: number; h: number }[],
  rtree: RBush<BoxItem>,
  G: number,
  maxExpansions: number,
  bendWeight: number,
  softCost: number, // cost added when moving through existing edge corridors
): XY[] | null {
  const blocked = (p: XY) => {
    for (const r of obstacleRects) {
      if (p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h) return true;
    }
    return false;
  };

  const toSnap = (p: XY) => ({ x: snapTo(p.x, G), y: snapTo(p.y, G) });
  const S = toSnap(start);
  const T = toSnap(end);

  type Rec = { p: XY; g: number; f: number; dir?: number; parent?: string };
  const key = (p: XY) => `${p.x},${p.y}`;
  const parse = (k: string): XY => {
    const [xs, ys] = k.split(",");
    return { x: Number(xs), y: Number(ys) };
  };

  const open = new Map<string, Rec>();
  const byF: string[] = [];
  const parents = new Map<string, string | undefined>();
  const closed = new Set<string>();

  function h(p: XY) {
    return manhattan(p, T);
  }

  function cellSoftPenalty(p: XY) {
    const bb = { minX: p.x - G / 2, minY: p.y - G / 2, maxX: p.x + G / 2, maxY: p.y + G / 2 };
    const hits = rtree.search(bb as any);
    let k = 0;
    for (const it of hits) if (it.kind === "edge") k++;
    return k * softCost;
  }

  function push(p: XY, g: number, dir?: number, parent?: string) {
    const k = key(p);
    const rec: Rec = { p, g, f: g + h(p), dir, parent };
    open.set(k, rec);
    parents.set(k, parent);
    byF.push(k);
    // dedupe/sort
    for (let i = byF.length - 1; i >= 0; i--) if (!open.has(byF[i])) byF.splice(i, 1);
    byF.sort((a, b) => open.get(a)!.f - open.get(b)!.f || a.localeCompare(b));
  }

  push(S, 0);
  let expansions = 0;

  while (byF.length && expansions < maxExpansions) {
    const k0 = byF.shift()!;
    const cur = open.get(k0)!;
    open.delete(k0);
    if (closed.has(k0)) continue;
    closed.add(k0);
    expansions++;

    if (cur.p.x === T.x && cur.p.y === T.y) {
      const chain: XY[] = [];
      let kk: string | undefined = k0;
      while (kk) {
        chain.push(parse(kk));
        kk = parents.get(kk);
      }
      chain.reverse();
      const out = compress([S, ...chain, T]);
      return out;
    }

    const dirs: XY[] = [
      { x: G, y: 0 },
      { x: -G, y: 0 },
      { x: 0, y: G },
      { x: 0, y: -G },
    ];
    for (let di = 0; di < 4; di++) {
      const d = dirs[di];
      const np = { x: cur.p.x + d.x, y: cur.p.y + d.y };
      const nk = key(np);
      if (blocked(np) || closed.has(nk)) continue;
      const turn = cur.dir != null && cur.dir !== di ? bendWeight : 0;
      const soft = cellSoftPenalty(np);
      push(np, cur.g + 1 + turn + soft, di, k0);
    }
  }
  return null;
}

/* ───────────────────────── Candidate sides & slots ───────────────────────── */

function pickCandidateSides(
  a: { x: number; y: number; w: number; h: number },
  b: { x: number; y: number; w: number; h: number },
): { srcSides: PortSide[]; dstSides: PortSide[]; axis: "H" | "V" } {
  const ac = center(a);
  const bc = center(b);
  const d = { x: bc.x - ac.x, y: bc.y - ac.y };
  const axis: "H" | "V" = Math.abs(d.x) >= Math.abs(d.y) ? "H" : "V";
  const s: PortSide[] = ["l", "r", "t", "b"];
  const src: PortSide[] = [];
  const dst: PortSide[] = [];
  for (const x of s) if (dot(sideNormal(x), d) > 0) src.push(x);
  for (const x of s.map((k) => k.toUpperCase() as PortSide))
    if (dot(sideNormal(x), { x: -d.x, y: -d.y }) > 0) dst.push(x);

  // always include facing pair
  if (axis === "H") {
    if (!src.includes("r")) src.push("r");
    if (!dst.includes("L")) dst.push("L");
    if (!src.includes("l")) src.push("l");
    if (!dst.includes("R")) dst.push("R");
  } else {
    if (!src.includes("b")) src.push("b");
    if (!dst.includes("T")) dst.push("T");
    if (!src.includes("t")) src.push("t");
    if (!dst.includes("B")) dst.push("B");
  }
  return { srcSides: src, dstSides: dst, axis };
}

function tryL(
  start: XY,
  end: XY,
  obstacles: { x: number; y: number; w: number; h: number }[],
): XY[] | null {
  const p1: XY = { x: end.x, y: start.y };
  const p2: XY = { x: start.x, y: end.y };
  const a = [start, p1, end];
  const b = [start, p2, end];

  const hit = (path: XY[]) =>
    obstacles.some(
      (r) =>
        rectIntersectsSegment(r, path[0], path[1]) || rectIntersectsSegment(r, path[1], path[2]),
    );

  if (!hit(a)) return a;
  if (!hit(b)) return b;
  return null;
}

/* ───────────────────────── Public API ───────────────────────── */

export function getNodeBoxes(nodes: Node[]) {
  const map = new Map<string, { x: number; y: number; w: number; h: number }>();
  for (const n of nodes) {
    const w = (n.width ?? (n.style as any)?.width ?? 160) as number;
    const h = (n.height ??
      (n.style as any)?.height ??
      (n.type === "eventNode" ? 36 : 120)) as number;
    map.set(n.id, { x: n.position.x, y: n.position.y, w, h });
  }
  return map;
}

export function routeEdges(
  nodes: Node[],
  edges: Edge[],
  cfg: RouterConfig,
  changedNodeIds?: Set<string>,
): { edges: RoutedEdge[]; diagnostics: RouterDiagnostics } {
  const boxes = getNodeBoxes(nodes);
  const inflated: Record<string, { x: number; y: number; w: number; h: number }> = {};
  for (const [id, b] of boxes.entries()) inflated[id] = inflate(b, cfg.node_margin);

  // RBush index: nodes (hard) and routed edge corridors (soft)
  const rtree = new RBush<BoxItem>();
  for (const b of Object.values(inflated)) {
    rtree.insert({ minX: b.x, minY: b.y, maxX: b.x + b.w, maxY: b.y + b.h, kind: "node" });
  }

  // group parallel edges (same source & target) for lane offsets (Rule 6)
  const pairMap = new Map<string, number[]>();
  edges.forEach((e, i) => {
    const k = `${e.source}→${e.target}`;
    (pairMap.get(k) || pairMap.set(k, []).get(k)!).push(i);
  });

  // side usage counters to score crowding
  const sideUse = new Map<string, number>();

  // estimate corridor crossing cost by counting overlaps with R-tree "edge" items
  function estimateCrossCost(sp: XY, tp: XY): number {
    const bb = segmentBBox(sp, tp, cfg.wire_gap);
    const hits = rtree.search(bb as any);
    let k = 0;
    for (const it of hits) if (it.kind === "edge") k++;
    return k * cfg.weights.gamma;
  }

  // prefer keeping previous side/slot (hysteresis)
  function sideChangePenalty(eid: Edge, sSide: PortSide, tSide: PortSide): number {
    const last = (eid.data as any)?._lastSides as { s: string; t: string } | undefined;
    if (!last) return 0;
    const sPenalty = last.s && last.s[0] !== sSide ? cfg.weights.delta : 0;
    const tPenalty = last.t && last.t[0] !== tSide ? cfg.weights.delta : 0;
    return sPenalty + tPenalty;
  }

  function allocSlot(nodeId: string, side: PortSide): number {
    const k = keySS(nodeId, side);
    const used = sideUse.get(k) ?? 0;
    sideUse.set(k, used + 1);
    // grow slot count as needed (Rule 1)
    return Math.min(cfg.portsPerSide - 1, used);
  }

  // Pre-pass: build a deterministic order by Manhattan distance (Rule 11)
  const order = edges
    .map((e, idx) => ({ e, idx }))
    .sort((A, B) => {
      const sa = boxes.get(A.e.source);
      const ta = boxes.get(A.e.target);
      const sb = boxes.get(B.e.source);
      const tb = boxes.get(B.e.target);
      const ma = sa && ta ? manhattan(center(sa), center(ta)) : 0;
      const mb = sb && tb ? manhattan(center(sb), center(tb)) : 0;
      return ma - mb || A.idx - B.idx;
    });

  const out: RoutedEdge[] = new Array(edges.length);
  let bendsSum = 0;
  let rerouted = 0;
  let crossings = 0;

  for (const { e, idx } of order) {
    const sBox = boxes.get(e.source);
    const tBox = boxes.get(e.target);
    if (!sBox || !tBox) {
      out[idx] = e as RoutedEdge;
      continue;
    }

    // Skip recomputation if neither endpoint changed and we already had waypoints (incremental)
    const prevWP = (e.data as any)?.waypoints as XY[] | undefined;
    if (
      prevWP &&
      changedNodeIds &&
      !changedNodeIds.has(e.source) &&
      !changedNodeIds.has(e.target)
    ) {
      out[idx] = e as RoutedEdge;
      continue;
    }

    const { srcSides, dstSides } = pickCandidateSides(sBox, tBox);

    // Try existing handles first (stability)
    const prevSrc = (e.sourceHandle as string) || (e.data as any)?._lastSides?.s;
    const prevDst = (e.targetHandle as string) || (e.data as any)?._lastSides?.t;
    let sSide: PortSide | undefined = (prevSrc && (prevSrc[0] as PortSide)) || undefined;
    let tSide: PortSide | undefined = (prevDst && (prevDst[0] as PortSide)) || undefined;

    let sSlot = Number.isFinite(Number(prevSrc?.slice(1))) ? Number(prevSrc!.slice(1)) : undefined;
    let tSlot = Number.isFinite(Number(prevDst?.slice(1))) ? Number(prevDst!.slice(1)) : undefined;

    // If any side is missing, score candidates (Rule 1: C = L + α*bends + β*crowd + γ*cross + δ*sideChange)
    if (!sSide || !tSide) {
      let best: { s: PortSide; t: PortSide; ss: number; ts: number; cost: number } | null = null;
      for (const s of srcSides) {
        for (const t of dstSides) {
          const ss = sSlot ?? allocSlot(e.source, s);
          const ts = tSlot ?? allocSlot(e.target, t);
          const sp = portPoint(sBox, s, ss, cfg.portsPerSide, cfg.egress_len);
          const tp = portPoint(tBox, t, ts, cfg.portsPerSide, cfg.egress_len);

          // try straight vs L to estimate bends
          const bends = sp.x === tp.x || sp.y === tp.y ? 0 : 1;
          const L = manhattan(sp, tp);
          const crowd =
            ((sideUse.get(keySS(e.source, s)) ?? 0) + (sideUse.get(keySS(e.target, t)) ?? 0)) ** 2;
          const cross = estimateCrossCost(sp, tp);
          const sidePenalty = sideChangePenalty(e, s, t);
          const cost =
            L + cfg.weights.alpha * bends + cfg.weights.beta * crowd + cross + sidePenalty;

          if (!best || cost < best.cost) best = { s, t, ss, ts, cost };
        }
      }
      if (best) {
        sSide = best.s;
        tSide = best.t;
        sSlot ??= best.ss;
        tSlot ??= best.ts;
      } else {
        // fallback: face pair
        sSide = "r";
        tSide = "L";
        sSlot ??= 0;
        tSlot ??= 0;
      }
    } else {
      // side chosen by history; still bump usage so next edges spread
      allocSlot(e.source, sSide);
      allocSlot(e.target, tSide);
      sSlot ??= allocSlot(e.source, sSide);
      tSlot ??= allocSlot(e.target, tSide);
    }

    const sp = portPoint(sBox, sSide!, sSlot!, cfg.portsPerSide, cfg.egress_len);
    const tp = portPoint(tBox, tSide!, tSlot!, cfg.portsPerSide, cfg.egress_len);

    // Primary routing (Rule 2)
    const otherObstacles = Object.entries(inflated)
      .filter(([id]) => id !== e.source && id !== e.target)
      .map(([, r]) => r);

    let way: XY[] | null = null;
    // Straight LOS
    if (
      (sp.x === tp.x || sp.y === tp.y) &&
      !otherObstacles.some((r) => rectIntersectsSegment(r, sp, tp))
    ) {
      way = [sp, tp];
    }
    // Manhattan L
    if (!way) way = tryL(sp, tp, otherObstacles);

    // Near-corner assist: turn at nearest free corner of either box
    if (!way) {
      const corners = [
        { x: sBox.x, y: sBox.y },
        { x: sBox.x + sBox.w, y: sBox.y },
        { x: sBox.x, y: sBox.y + sBox.h },
        { x: sBox.x + sBox.w, y: sBox.y + sBox.h },
        { x: tBox.x, y: tBox.y },
        { x: tBox.x + tBox.w, y: tBox.y },
        { x: tBox.x, y: tBox.y + tBox.h },
        { x: tBox.x + tBox.w, y: tBox.y + tBox.h },
      ];
      corners.sort((a, b) => manhattan(sp, a) - manhattan(sp, b));
      for (const c of corners) {
        const cp = { x: snapTo(c.x, cfg.G), y: snapTo(c.y, cfg.G) };
        const candidate = tryL(sp, cp, otherObstacles) ?? tryL(cp, tp, otherObstacles);
        if (candidate) {
          way = [sp, cp, tp];
          break;
        }
      }
    }

    // Secondary routing (Rule 3): A* with soft corridor costs
    if (!way) {
      const path = astar(
        sp,
        tp,
        otherObstacles,
        rtree,
        cfg.G,
        cfg.maxAStarExpansions,
        cfg.weights.bend_weight,
        Math.max(1, Math.floor(cfg.weights.gamma / 6)),
      );
      if (path) way = path;
    }

    // Absolute fallback: simple L
    if (!way) way = [sp, { x: sp.x, y: tp.y }, tp];

    // Grid–snap and compress
    way = way.map((p) => ({ x: snapTo(p.x, cfg.G), y: snapTo(p.y, cfg.G) }));
    way = compress(way);

    bendsSum += Math.max(0, way.length - 2);
    rerouted++;

    // Insert edge corridor boxes for crossing control (Rule 4)
    const items = corridorBoxes(way, cfg.wire_gap);
    items.forEach((it) => rtree.insert(it));
    crossings += rtree
      .search(segmentBBox(way[0], way[way.length - 1], cfg.wire_gap) as any)
      .filter((x) => x.kind === "edge").length;

    out[idx] = {
      ...(e as Edge),
      sourceHandle: `${sSide}${sSlot}`,
      targetHandle: `${tSide}${tSlot}`,
      data: {
        ...(e.data ?? {}),
        waypoints: way,
        cornerR: cfg.corner_radius,
        sourcePort: { side: sSide!, slot: sSlot! },
        targetPort: { side: tSide!, slot: tSlot! },
        _lastSides: { s: `${sSide}${sSlot}`, t: `${tSide}${tSlot}` },
      },
    };
  }

  /* Rule 6: Apply lane offsets for parallel edges (±k·wire_gap) */
  for (const ids of pairMap.values()) {
    if (ids.length <= 1) continue;
    // stable order
    ids.sort((a, b) => a - b);
    const n = ids.length;
    for (let i = 0; i < n; i++) {
      const k = i - (n - 1) / 2; // symmetric around 0
      const laneOffset = k * (cfg.wire_gap / 2);
      const re = out[ids[i]];
      if (!re) continue;
      re.data = { ...(re.data ?? {}), laneOffset };
    }
  }

  const diag: RouterDiagnostics = {
    crossings,
    avg_bends: out.length ? bendsSum / out.length : 0,
    reroutedCount: rerouted,
  };
  return { edges: out, diagnostics: diag };
}

export const defaultRouterConfig: RouterConfig = {
  node_margin: 8,
  wire_gap: 10,
  egress_len: 12,
  min_egress: 6,
  corner_radius: 6,
  G: 12,
  P: 24,
  edge_padding: 12,
  grow_step: 32,
  min_wrapper_w: 320,
  min_wrapper_h: 220,
  weights: { alpha: 12, beta: 4, gamma: 30, delta: 6, bend_weight: 8 },
  portsPerSide: 32,
  maxAStarExpansions: 4000,
};
