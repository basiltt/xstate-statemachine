//  src/xstate_statemachine/inspector/frontend/src/components/statechart/diagram/hooks/router.ts

// Lightweight rectilinear router with side/slot selection and L/A* fallback
// Implements a practical subset of the provided rule set with deterministic output.

import type { Edge, Node } from "reactflow";

export type PortSide = "l" | "r" | "t" | "b" | "L" | "R" | "T" | "B";
type XY = { x: number; y: number };

export type RouterConfig = {
  node_margin: number; // inflate obstacles
  wire_gap: number;
  egress_len: number;
  min_egress: number;
  corner_radius: number;
  G: number; // grid size
  P: number; // wrapper padding (unused here, for diagnostics)
  edge_padding: number;
  weights: { alpha: number; beta: number; gamma: number; delta: number; bend_weight: number };
  portsPerSide: number;
  maxAStarExpansions: number;
};

export type RoutedEdge = Edge & {
  data?: Edge["data"] & {
    waypoints?: XY[];
    sourcePort?: { side: string; slot: number };
    targetPort?: { side: string; slot: number };
  };
};

export type RouterDiagnostics = { crossings: number; avg_bends: number; reroutedCount: number };

export function getNodeBoxes(nodes: Node[]) {
  const map = new Map<string, { x: number; y: number; w: number; h: number }>();
  for (const n of nodes) {
    const w = (n.width ?? (n.style as any)?.width ?? 160) as number;
    const h = (n.height ?? (n.style as any)?.height ?? 120) as number;
    map.set(n.id, { x: n.position.x, y: n.position.y, w, h });
  }
  return map;
}

function inflate(b: { x: number; y: number; w: number; h: number }, m: number) {
  return { x: b.x - m, y: b.y - m, w: b.w + 2 * m, h: b.h + 2 * m };
}

function rectIntersectsSegment(
  rect: { x: number; y: number; w: number; h: number },
  a: XY,
  b: XY,
): boolean {
  // Axis-aligned rectangles and horizontal/vertical segments only (our router ensures this)
  const minX = Math.min(a.x, b.x);
  const maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const maxY = Math.max(a.y, b.y);
  const r = rect;
  // Quick reject
  if (maxX < r.x || minX > r.x + r.w || maxY < r.y || minY > r.y + r.h) return false;
  // Further check overlap when segment crosses rect projection
  const isH = a.y === b.y;
  if (isH) {
    const y = a.y;
    return y >= r.y && y <= r.y + r.h && !(maxX < r.x || minX > r.x + r.w);
  } else {
    const x = a.x;
    return x >= r.x && x <= r.x + r.w && !(maxY < r.y || minY > r.y + r.h);
  }
}

function manhattan(a: XY, b: XY) {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

function sideNormal(side: PortSide): XY {
  switch (side) {
    case "l":
    case "L":
      return { x: -1, y: 0 };
    case "r":
    case "R":
      return { x: 1, y: 0 };
    case "t":
    case "T":
      return { x: 0, y: -1 };
    case "b":
    case "B":
      return { x: 0, y: 1 };
  }
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

function snapTo(v: number, G: number) {
  return Math.round(v / G) * G;
}

function dot(a: XY, b: XY) {
  return a.x * b.x + a.y * b.y;
}

function pickCandidateSides(
  a: { x: number; y: number; w: number; h: number },
  b: { x: number; y: number; w: number; h: number },
): { srcSides: PortSide[]; dstSides: PortSide[]; axis: "H" | "V" } {
  const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 };
  const bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
  const d = { x: bc.x - ac.x, y: bc.y - ac.y };
  const axis = Math.abs(d.x) >= Math.abs(d.y) ? "H" : "V";
  const srcCandidates: PortSide[] = [];
  const dstCandidates: PortSide[] = [];
  const sides: PortSide[] = ["l", "r", "t", "b"];
  for (const s of sides) if (dot(sideNormal(s), d) > 0) srcCandidates.push(s);
  for (const s of sides.map((x) => x.toUpperCase() as PortSide))
    if (dot(sideNormal(s), { x: -d.x, y: -d.y }) > 0) dstCandidates.push(s);

  // Always include facing pair
  if (axis === "H") {
    if (!srcCandidates.includes("r")) srcCandidates.push("r");
    if (!dstCandidates.includes("L")) dstCandidates.push("L");
    if (!srcCandidates.includes("l")) srcCandidates.push("l");
    if (!dstCandidates.includes("R")) dstCandidates.push("R");
  } else {
    if (!srcCandidates.includes("b")) srcCandidates.push("b");
    if (!dstCandidates.includes("T")) dstCandidates.push("T");
    if (!srcCandidates.includes("t")) srcCandidates.push("t");
    if (!dstCandidates.includes("B")) dstCandidates.push("B");
  }
  return { srcSides: srcCandidates, dstSides: dstCandidates, axis };
}

function segmentHitsAny(
  obstacles: { x: number; y: number; w: number; h: number }[],
  a: XY,
  b: XY,
): boolean {
  for (const r of obstacles) if (rectIntersectsSegment(r, a, b)) return true;
  return false;
}

function tryLPath(
  start: XY,
  end: XY,
  obstacles: { x: number; y: number; w: number; h: number }[],
): XY[] | null {
  const p1: XY = { x: end.x, y: start.y };
  const p2: XY = { x: start.x, y: end.y };
  const a = [start, p1, end];
  const b = [start, p2, end];
  const clearA = !segmentHitsAny(obstacles, a[0], a[1]) && !segmentHitsAny(obstacles, a[1], a[2]);
  if (clearA) return a;
  const clearB = !segmentHitsAny(obstacles, b[0], b[1]) && !segmentHitsAny(obstacles, b[1], b[2]);
  if (clearB) return b;
  return null;
}

function compress(points: XY[]): XY[] {
  const out: XY[] = [];
  for (const p of points) {
    const n = out.length;
    if (n >= 2) {
      const a = out[n - 2];
      const b = out[n - 1];
      // If a->b and b->p are colinear, drop b
      if ((a.x === b.x && b.x === p.x) || (a.y === b.y && b.y === p.y)) {
        out[n - 1] = p;
        continue;
      }
    }
    out.push(p);
  }
  return out;
}

// Very small A* on rectilinear grid
function astar(
  start: XY,
  end: XY,
  obstacles: { x: number; y: number; w: number; h: number }[],
  G: number,
  maxExpansions: number,
  bendWeight: number,
): XY[] | null {
  const key = (p: XY) => `${p.x},${p.y}`;
  const parse = (k: string): XY => {
    const [xs, ys] = k.split(",");
    return { x: Number(xs), y: Number(ys) };
  };
  const blocked = (p: XY) => {
    for (const r of obstacles)
      if (p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h) return true;
    return false;
  };
  const startS = { x: snapTo(start.x, G), y: snapTo(start.y, G) };
  const endS = { x: snapTo(end.x, G), y: snapTo(end.y, G) };
  type NodeRec = { p: XY; g: number; f: number; dir?: number; parent?: string };
  const open = new Map<string, NodeRec>();
  const parents = new Map<string, string | undefined>();
  const byF: string[] = [];

  function push(p: XY, g: number, dir?: number, parent?: string) {
    const h = manhattan(p, endS);
    const f = g + h;
    const k = key(p);
    const rec: NodeRec = { p, g, f, dir, parent };
    open.set(k, rec);
    parents.set(k, parent);
    byF.push(k);
    // Remove stale keys not in open (e.g., duplicates that were closed)
    for (let i = byF.length - 1; i >= 0; i--) if (!open.has(byF[i])) byF.splice(i, 1);
    byF.sort((a, b) => (open.get(a)?.f ?? Infinity) - (open.get(b)?.f ?? Infinity));
  }

  push(startS, 0);
  const closed = new Set<string>();
  let expansions = 0;
  while (byF.length && expansions < maxExpansions) {
    const k = byF.shift()!;
    const cur = open.get(k)!;
    open.delete(k);
    if (closed.has(k)) continue;
    closed.add(k);
    expansions++;
    if (cur.p.x === endS.x && cur.p.y === endS.y) {
      // Reconstruct using parents map and key parsing
      const chain: XY[] = [];
      let kk: string | undefined = k;
      while (kk) {
        chain.push(parse(kk));
        kk = parents.get(kk);
      }
      chain.reverse();
      return compress([startS, ...chain, endS]);
    }
    // neighbors
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
      push(np, cur.g + 1 + turn, di, k);
    }
  }
  return null;
}

function slotsNextIndex(count: number, max: number) {
  return Math.min(max - 1, count);
}

export function routeEdges(
  nodes: Node[],
  edges: Edge[],
  cfg: RouterConfig,
  _changedNodeIds?: Set<string>,
): { edges: RoutedEdge[]; diagnostics: RouterDiagnostics } {
  const boxes = getNodeBoxes(nodes);
  const inflObstacles = new Map<string, { x: number; y: number; w: number; h: number }>();
  boxes.forEach((b, id) => inflObstacles.set(id, inflate(b, cfg.node_margin)));
  // changedNodeIds is reserved for incremental routing optimizations.

  const sideUse = new Map<string, number>(); // key: node|side
  const result: RoutedEdge[] = [];
  let bendsSum = 0;
  let rerouted = 0;

  function allocSlot(nodeId: string, side: PortSide): number {
    const k = `${nodeId}|${side}`;
    const used = sideUse.get(k) ?? 0;
    const slot = slotsNextIndex(used, cfg.portsPerSide);
    sideUse.set(k, used + 1);
    return slot;
  }

  const parseHandle = (h: string | null | undefined): { side?: PortSide; slot?: number } => {
    if (!h || typeof h !== "string" || h.length === 0) return {};
    const sideChar = h.charAt(0) as PortSide;
    const valid = ["l", "r", "t", "b", "L", "R", "T", "B"] as const;
    if (!(valid as readonly string[]).includes(sideChar)) return {} as any;
    const num = Number.parseInt(h.slice(1));
    return { side: sideChar, slot: Number.isFinite(num) ? Math.max(0, num) : undefined } as any;
  };

  for (const e of edges) {
    const s = boxes.get(e.source);
    const t = boxes.get(e.target);
    if (!s || !t) {
      result.push(e as RoutedEdge);
      continue;
    }

    // 1) Prefer existing handles if present to stabilize routing
    const sParsed = parseHandle(e.sourceHandle as any);
    const tParsed = parseHandle(e.targetHandle as any);
    let sSide: PortSide | undefined = sParsed.side;
    let tSide: PortSide | undefined = tParsed.side;
    let sSlot: number | undefined = sParsed.slot;
    let tSlot: number | undefined = tParsed.slot;

    if (!sSide || !tSide) {
      // 2) Fallback to picking the best facing sides if any side handle missing
      const { srcSides, dstSides } = pickCandidateSides(s, t);
      let best: {
        sSide: PortSide;
        tSide: PortSide;
        cost: number;
        sSlot: number;
        tSlot: number;
      } | null = null;
      for (const sS of srcSides) {
        for (const tS of dstSides) {
          const sUsed = sideUse.get(`${e.source}|${sS}`) ?? 0;
          const tUsed = sideUse.get(`${e.target}|${tS}`) ?? 0;
          const ss = slotsNextIndex(sUsed, cfg.portsPerSide);
          const ts = slotsNextIndex(tUsed, cfg.portsPerSide);
          const sp0 = portPoint(s, sS, ss, cfg.portsPerSide, cfg.egress_len);
          const tp0 = portPoint(t, tS, ts, cfg.portsPerSide, cfg.egress_len);
          const L = manhattan(sp0, tp0);
          const bends = sp0.x === tp0.x || sp0.y === tp0.y ? 0 : 1;
          const crowd = (sUsed + tUsed) ** 2;
          const penalty = cfg.weights.alpha * bends + cfg.weights.beta * crowd;
          const cost = L + penalty;
          if (!best || cost < best.cost)
            best = { sSide: sS, tSide: tS, cost, sSlot: ss, tSlot: ts };
        }
      }
      if (!best) {
        result.push(e as RoutedEdge);
        continue;
      }
      sSide = best.sSide;
      tSide = best.tSide;
      // Use tentative slots if none parsed
      sSlot ??= best.sSlot;
      tSlot ??= best.tSlot;
    }

    // Allocate final slots (mutate counters once). If a slot was parsed, keep it but ensure
    // side usage is incremented for fairness in subsequent edges.
    if (sSide == null || tSide == null) {
      result.push(e as RoutedEdge);
      continue;
    }
    const sKey = `${e.source}|${sSide}`;
    const tKey = `${e.target}|${tSide}`;
    if (sSlot == null) sSlot = allocSlot(e.source, sSide);
    else sideUse.set(sKey, (sideUse.get(sKey) ?? 0) + 1);
    if (tSlot == null) tSlot = allocSlot(e.target, tSide);
    else sideUse.set(tKey, (sideUse.get(tKey) ?? 0) + 1);

    const sp = portPoint(s, sSide, sSlot, cfg.portsPerSide, cfg.egress_len);
    const tp = portPoint(t, tSide, tSlot, cfg.portsPerSide, cfg.egress_len);

    // Fast path: straight
    let way: XY[] | null = null;
    if (sp.x === tp.x || sp.y === tp.y) {
      // Check obstacle clear along the segment
      const obs = [...inflObstacles.entries()]
        .filter(([id]) => id !== e.source && id !== e.target)
        .map(([, r]) => r);
      if (!segmentHitsAny(obs, sp, tp)) way = [sp, tp];
    }
    // Try L
    if (!way) {
      const obs = [...inflObstacles.entries()]
        .filter(([id]) => id !== e.source && id !== e.target)
        .map(([, r]) => r);
      way = tryLPath(sp, tp, obs);
    }
    // A*
    if (!way) {
      const obs = [...inflObstacles.entries()]
        .filter(([id]) => id !== e.source && id !== e.target)
        .map(([, r]) => r);
      const path = astar(sp, tp, obs, cfg.G, cfg.maxAStarExpansions, cfg.weights.bend_weight);
      if (path) way = path;
    }

    if (!way) way = [sp, { x: sp.x, y: tp.y }, tp];
    bendsSum += Math.max(0, way.length - 2);
    rerouted++;

    // Snap
    way = way.map((p) => ({ x: snapTo(p.x, cfg.G), y: snapTo(p.y, cfg.G) }));
    way = compress(way);

    result.push({
      ...(e as Edge),
      sourceHandle: `${sSide}${sSlot}`,
      targetHandle: `${tSide}${tSlot}`,
      data: {
        ...(e.data ?? {}),
        waypoints: way,
        sourcePort: { side: sSide, slot: sSlot },
        targetPort: { side: tSide, slot: tSlot },
      },
    });
  }

  const diag: RouterDiagnostics = {
    crossings: 0,
    avg_bends: result.length ? bendsSum / result.length : 0,
    reroutedCount: rerouted,
  };
  return { edges: result, diagnostics: diag };
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
  weights: { alpha: 12, beta: 4, gamma: 30, delta: 6, bend_weight: 8 },
  portsPerSide: 24,
  maxAStarExpansions: 2000,
};
