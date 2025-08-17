// src/xstate_statemachine/inspector/frontend/src/components/statechart/layout.ts

import type { Edge, Node } from "reactflow";
import { EDGE_CLEAR_TOP, estimateReservedTop, GRID_SIZE, PADDING, ROOT_HEADER } from "./constants";

/* ──────────────────────────────────────────────────────────────────────────
   Size & spacing (visual hints; React Flow will measure true sizes later)
   ────────────────────────────────────────────────────────────────────────── */
const STATE_W = 260; // fixed width; height is auto in component
const STATE_H_HINT = 140; // only used for column packing
const EVENT_W = 140;
const EVENT_H_HINT = 36;

const COL_GAP = 180;
const ROW_GAP = 100;

// more wrapper inner padding per request
const INNER_PAD_X = (PADDING ?? 40) + 64;
const INNER_PAD_Y = (PADDING ?? 40) + 56;

// grid snapping so edges become perfectly straight when aligned
const GRID = 8;
const snap = (v: number) => Math.round(v / GRID) * GRID;

/* ──────────────────────────────────────────────────────────────────────────
   Types & helpers
   ────────────────────────────────────────────────────────────────────────── */
type MachineDef = {
  id?: string;
  initial?: string;
  states?: Record<string, any>;
  on?: Record<string, any>;
};

type FlatState = { id: string; key: string; def: any };
type TEdge = { source: string; target: string; label: string };

const toArr = <T>(x?: T | T[]) => (!x ? [] : Array.isArray(x) ? x : [x]);
const hasBody = (def: any) =>
  toArr(def?.entry).length +
    toArr(def?.exit).length +
    toArr(def?.invoke).length +
    toArr(def?.activities).length >
  0;

function collectStates(def: MachineDef, prefix = ""): FlatState[] {
  const out: FlatState[] = [];
  for (const key of Object.keys(def.states ?? {})) {
    const s = (def.states as any)[key] ?? {};
    const id = prefix ? `${prefix}.${key}` : key;
    out.push({ id, key, def: s });
    if (s.states) out.push(...collectStates(s as MachineDef, id));
  }
  return out;
}

function normalizeTargets(t: any): string[] {
  if (!t) return [];
  if (typeof t === "string") return [t];
  if (Array.isArray(t)) return t.flatMap(normalizeTargets);
  if (typeof t === "object" && t.target) return normalizeTargets(t.target);
  return [];
}

function collectTransitions(def: MachineDef, prefix = ""): TEdge[] {
  const out: TEdge[] = [];
  const mk = (k: string) => (prefix ? `${prefix}.${k}` : k);

  if (def.on) {
    for (const evt of Object.keys(def.on)) {
      for (const tgt of normalizeTargets(def.on[evt])) {
        out.push({
          source: prefix || "ROOT",
          target: prefix ? `${prefix}.${tgt}` : tgt,
          label: evt,
        });
      }
    }
  }

  for (const key of Object.keys(def.states ?? {})) {
    const s = (def.states as any)[key] ?? {};
    const sid = mk(key);

    if (s.on) {
      for (const evt of Object.keys(s.on)) {
        for (const tgt of normalizeTargets(s.on[evt])) {
          const tid = tgt.startsWith("#") ? tgt.slice(1) : tgt.includes(".") ? tgt : mk(tgt);
          out.push({ source: sid, target: tid, label: evt });
        }
      }
    }

    if (s.states) out.push(...collectTransitions(s as MachineDef, sid));
  }
  return out;
}

/* ──────────────────────────────────────────────────────────────────────────
   Left→Right layered layout (Sugiyama-ish; cycle tolerant)
   ────────────────────────────────────────────────────────────────────────── */
function buildLayers(
  ids: string[],
  edges: { source: string; target: string }[],
  initial?: string,
): string[][] {
  const idSet = new Set(ids);
  const indeg = new Map<string, number>(ids.map((id) => [id, 0]));
  const adj = new Map<string, Set<string>>();
  for (const id of ids) adj.set(id, new Set());
  for (const e of edges) {
    if (!idSet.has(e.source) || !idSet.has(e.target)) continue;
    if (!adj.get(e.source)!.has(e.target)) {
      adj.get(e.source)!.add(e.target);
      indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1);
    }
  }

  const q: string[] = [];
  if (initial && idSet.has(initial)) q.push(initial);
  for (const id of ids) if ((indeg.get(id) ?? 0) === 0 && id !== initial) q.push(id);
  if (q.length === 0) q.push(...[...ids].sort());

  const layers: string[][] = [];
  const seen = new Set<string>();

  while (seen.size < ids.length) {
    const frontier = q.filter((id) => !seen.has(id));
    if (frontier.length === 0) {
      const rem = ids.filter((id) => !seen.has(id));
      if (!rem.length) break;
      frontier.push(...rem.slice(0, Math.max(1, Math.ceil(rem.length / 2))));
    }
    layers.push(frontier);
    frontier.forEach((id) => seen.add(id));

    const next: string[] = [];
    for (const id of frontier) for (const t of adj.get(id) ?? []) if (!seen.has(t)) next.push(t);
    q.length = 0;
    const uniq = new Set<string>();
    for (const id of next)
      if (!uniq.has(id)) {
        uniq.add(id);
        q.push(id);
      }
  }

  // barycenter crossing reduction
  const idx = new Map<string, number>();
  layers.forEach((col, i) => col.forEach((id) => idx.set(id, i)));
  for (let i = 1; i < layers.length; i++) {
    const prev = new Set(layers[i - 1]);
    const incoming: Record<string, number[]> = {};
    for (const e of edges) {
      if (idx.get(e.target) === i && prev.has(e.source)) {
        (incoming[e.target] ||= []).push(layers[i - 1].indexOf(e.source));
      }
    }
    const mean = (xs: number[]) => (xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : 0);
    layers[i].sort((a, b) => mean(incoming[a] ?? []) - mean(incoming[b] ?? []));
  }

  return layers;
}

/* ──────────────────────────────────────────────────────────────────────────
   Positioning (snapped to grid)
   ────────────────────────────────────────────────────────────────────────── */
type XY = { x: number; y: number };

function positionStates(layers: string[][], reservedTop: number): Record<string, XY> {
  const pos: Record<string, XY> = {};
  let x = INNER_PAD_X;

  for (const col of layers) {
    const totalH = col.length * STATE_H_HINT + Math.max(0, col.length - 1) * ROW_GAP;
    let y = reservedTop + INNER_PAD_Y + Math.max(0, (0 - totalH) / 2);
    for (const id of col) {
      pos[id] = { x: snap(x), y: snap(y) };
      y += STATE_H_HINT + ROW_GAP;
    }
    x += STATE_W + COL_GAP;
  }

  return pos;
}

function sanitizeEventId(label: string) {
  return label.replace(/[^a-zA-Z0-9_]+/g, "_");
}

/** pack event pills into banded rows between source/target columns, avoiding one long global rail */
function positionEvents(
  labels: string[],
  transitions: TEdge[],
  statePos: Record<string, XY>,
  reservedTop: number,
  widthHint: number,
  layerOf: Map<string, number>,
  xOfLayer: (idx: number) => number,
): Record<string, XY> {
  const pos: Record<string, XY> = {};
  if (!labels.length) return pos;

  // Group transitions by label
  const byLabel = new Map<string, TEdge[]>();
  for (const t of transitions)
    (byLabel.get(t.label) || byLabel.set(t.label, []).get(t.label)!).push(t);

  // For each label, compute the span and preferred band (column) to place the event
  type BandKey = number; // integer layer index around which the event sits
  const bands: Map<BandKey, { rows: { y: number; occupied: Array<[number, number]> }[] }> =
    new Map();

  function getBand(layerIdx: number) {
    if (!bands.has(layerIdx)) bands.set(layerIdx, { rows: [] });
    return bands.get(layerIdx)!;
  }

  const minX = INNER_PAD_X;
  const maxX = Math.max(minX, widthHint - INNER_PAD_X - EVENT_W);
  const spacing = 16; // horizontal gap between events in same row
  const rowH = EVENT_H_HINT + 10;
  const baseY = reservedTop + Math.max(14, Math.floor(INNER_PAD_Y / 2));

  function placeInBand(layerIdx: number, desiredX: number) {
    const band = getBand(layerIdx);
    // find first row that can fit without overlap
    for (const r of band.rows) {
      // find a spot after the last occupied segment
      let x = desiredX;
      // ensure it doesn't collide with existing segments
      let collides = true;
      let guard = 0;
      while (collides && guard++ < 100) {
        collides = r.occupied.some(
          ([l, rgt]) => !(x + EVENT_W + spacing <= l || x >= rgt + spacing),
        );
        if (collides) x += spacing; // nudge right until free
        if (x > maxX) break;
      }
      if (!collides && x <= maxX) {
        r.occupied.push([x, x + EVENT_W]);
        return { x: snap(Math.max(minX, Math.min(maxX, x))), y: snap(r.y) };
      }
    }
    // need a new row
    const y = baseY + band.rows.length * rowH;
    const x = snap(Math.max(minX, Math.min(maxX, desiredX)));
    band.rows.push({ y, occupied: [[x, x + EVENT_W]] });
    return { x, y: snap(y) };
  }

  for (const label of labels) {
    const group = byLabel.get(label)!;
    // Handle self-loop: place directly above the state (first occurrence)
    const self = group.find((t) => t.source === t.target);
    if (self) {
      const s = statePos[self.source] ?? { x: INNER_PAD_X, y: baseY };
      const cx = snap(s.x + STATE_W / 2 - EVENT_W / 2);
      pos[`__event__${sanitizeEventId(label)}`] = {
        x: Math.max(minX, Math.min(maxX, cx)),
        y: baseY,
      };
      continue;
    }

    const cols = group.flatMap((t) => [layerOf.get(t.source) ?? 0, layerOf.get(t.target) ?? 0]);
    const minCol = Math.min(...cols);
    const maxCol = Math.max(...cols);
    const midCol = Math.round((minCol + maxCol) / 2);

    const xLeft = xOfLayer(minCol) + STATE_W / 2;
    const xRight = xOfLayer(maxCol) + STATE_W / 2;
    const cx = (xLeft + xRight) / 2 - EVENT_W / 2; // center between columns

    const placed = placeInBand(midCol, snap(cx));
    pos[`__event__${sanitizeEventId(label)}`] = placed;
  }

  return pos;
}

/* ──────────────────────────────────────────────────────────────────────────
   Handle picking (nearest sides, avoids inter-locking)
   ────────────────────────────────────────────────────────────────────────── */
function pickHandles(
  src: XY,
  dst: XY,
  srcW: number,
  srcH: number,
  dstW: number,
  dstH: number,
): { sh: string; th: string } {
  const sL = src.x,
    sT = src.y,
    sR = src.x + srcW,
    sB = src.y + srcH;
  const dL = dst.x,
    dT = dst.y,
    dR = dst.x + dstW,
    dB = dst.y + dstH;
  const scx = sL + srcW / 2,
    scy = sT + srcH / 2;
  const dcx = dL + dstW / 2,
    dcy = dT + dstH / 2;

  // Bands to prefer LR or TB when roughly aligned
  const vBandTop = dT + Math.min(24, dstH * 0.35);
  const vBandBot = dB - Math.min(24, dstH * 0.35);
  const inVerticalBand = scy >= vBandTop && scy <= vBandBot;

  const hBandLeft = dL + Math.min(36, dstW * 0.35);
  const hBandRight = dR - Math.min(36, dstW * 0.35);
  const inHorizontalBand = scx >= hBandLeft && scx <= hBandRight;

  if (inVerticalBand) {
    const dir = scx < dL ? "L" : scx > dR ? "R" : dcx >= scx ? "L" : "R";
    return dir === "L" ? { sh: "r", th: "L" } : { sh: "l", th: "R" };
  }
  if (inHorizontalBand) {
    const dir = scy < dT ? "T" : scy > dB ? "B" : dcy >= scy ? "T" : "B";
    return dir === "T" ? { sh: "b", th: "T" } : { sh: "t", th: "B" };
  }

  // Fallback: rectangle-to-rectangle cost with lateral penalties
  const dxC = dcx - scx;
  const dyC = dcy - scy;
  const lateralX = Math.abs(dyC) * 0.6;
  const lateralY = Math.abs(dxC) * 0.6;

  const costToLeft = Math.max(0, dL - sR) + lateralX;
  const costToRight = Math.max(0, sL - dR) + lateralX;
  const costToTop = Math.max(0, dT - sB) + lateralY;
  const costToBottom = Math.max(0, sT - dB) + lateralY;

  const candidates: Array<{ dir: "L" | "R" | "T" | "B"; sh: string; th: string; cost: number }> = [
    { dir: "L", sh: "r", th: "L", cost: costToLeft },
    { dir: "R", sh: "l", th: "R", cost: costToRight },
    { dir: "T", sh: "b", th: "T", cost: costToTop },
    { dir: "B", sh: "t", th: "B", cost: costToBottom },
  ];
  let best = candidates[0];
  for (const c of candidates) if (c.cost < best.cost) best = c;
  return { sh: best.sh, th: best.th };
}

/* ──────────────────────────────────────────────────────────────────────────
   Public API
   ────────────────────────────────────────────────────────────────────────── */
export async function getLayoutedElements(
  definition: MachineDef,
  context: Record<string, any> | undefined | null,
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const machineId = definition.id ?? "StateMachine";
  const rootId = `${machineId}__root`;

  const states = collectStates(definition);
  const stateIds = states.map((s) => s.id);
  const transitions = collectTransitions(definition).filter(
    (t) => stateIds.includes(t.source) && stateIds.includes(t.target),
  );

  const layers = buildLayers(
    stateIds,
    transitions.map(({ source, target }) => ({ source, target })),
    definition.initial,
  );

  const reservedTop = Math.max(
    estimateReservedTop(context) + EDGE_CLEAR_TOP,
    ROOT_HEADER + EDGE_CLEAR_TOP,
  );

  // positions
  const sPos = positionStates(layers, reservedTop);

  // Precompute layer index and x position per column for event banding
  const layerOf = new Map<string, number>();
  layers.forEach((col, i) => col.forEach((id) => layerOf.set(id, i)));
  const xOfLayer = (idx: number) => INNER_PAD_X + idx * (STATE_W + COL_GAP);

  // wrapper size hints
  const widthHint = Math.max(
    980,
    INNER_PAD_X * 2 + Math.max(STATE_W, layers.length * STATE_W + (layers.length - 1) * COL_GAP),
  );

  const tallest = Math.max(
    ...layers.map((col) => col.length * STATE_H_HINT + Math.max(0, col.length - 1) * ROW_GAP),
    STATE_H_HINT,
  );

  const heightHint = Math.max(560, reservedTop + INNER_PAD_Y * 2 + tallest);

  // root wrapper
  const nodes: Node[] = [
    {
      id: rootId,
      type: "rootNode",
      data: { label: machineId, context: context ?? {} },
      position: { x: GRID_SIZE ?? 8, y: GRID_SIZE ?? 8 },
      style: { width: widthHint, height: heightHint },
      draggable: true,
      selectable: false,
    },
  ];

  // states (auto-height: only width provided). headerOnly passed for empty states.
  for (const s of states) {
    const p = sPos[s.id] ?? { x: INNER_PAD_X, y: reservedTop + INNER_PAD_Y };
    nodes.push({
      id: s.id,
      type: s.def?.states ? "compoundStateNode" : "stateNode",
      data: { label: s.key, definition: s.def, machineId, headerOnly: !hasBody(s.def) },
      position: p,
      style: { width: STATE_W }, // height is automatic in component
      parentId: rootId,
      extent: "parent",
      draggable: true,
    });
  }

  // event nodes using banded placement
  const labels = Array.from(new Set(transitions.map((t) => t.label))).sort();
  const ePos = positionEvents(labels, transitions, sPos, reservedTop, widthHint, layerOf, xOfLayer);
  for (const label of labels) {
    const id = `__event__${sanitizeEventId(label)}`;
    const p = ePos[id] ?? { x: INNER_PAD_X, y: reservedTop + 12 };
    nodes.push({
      id,
      type: "eventNode",
      data: { label },
      position: p,
      style: { width: EVENT_W },
      parentId: rootId,
      extent: "parent",
      draggable: true,
    });
  }

  // edges: state -> event -> state, with nearest-side handles
  const edges: Edge[] = [];
  const evId = (lbl: string) => `__event__${sanitizeEventId(lbl)}`;
  const seenSE = new Set<string>();
  const seenET = new Set<string>();

  for (const t of transitions) {
    const e = evId(t.label);

    // state -> event
    const k1 = `${t.source}->${e}`;
    if (!seenSE.has(k1)) {
      seenSE.add(k1);
      const sh = pickHandles(
        sPos[t.source],
        ePos[e] ?? sPos[t.source],
        STATE_W,
        STATE_H_HINT,
        EVENT_W,
        EVENT_H_HINT,
      );
      edges.push({
        id: `e_se_${t.source}_${e}`,
        source: t.source,
        target: e,
        sourceHandle: sh.sh,
        targetHandle: sh.th,
        type: "transitionEdge",
        data: { label: "" }, // event label lives on the event node
      });
    }

    // event -> state
    const k2 = `${e}->${t.target}`;
    if (!seenET.has(k2)) {
      seenET.add(k2);
      const sh2 = pickHandles(
        ePos[e] ?? sPos[t.target],
        sPos[t.target],
        EVENT_W,
        EVENT_H_HINT,
        STATE_W,
        STATE_H_HINT,
      );
      edges.push({
        id: `e_et_${e}_${t.target}`,
        source: e,
        target: t.target,
        sourceHandle: sh2.sh,
        targetHandle: sh2.th,
        type: "transitionEdge",
        data: { label: "" },
      });
    }
  }

  // initial marker (top → down)
  if (definition.initial && stateIds.includes(definition.initial)) {
    const initId = "__initial__root";
    const cx = (sPos[definition.initial]?.x ?? INNER_PAD_X) + STATE_W / 2;
    nodes.push({
      id: initId,
      type: "initialNode",
      data: {},
      position: { x: snap(cx), y: Math.max(12, reservedTop - 56) },
      parentId: rootId,
      extent: "parent",
      draggable: false,
      selectable: false,
    });
    edges.push({
      id: `e_${initId}_${definition.initial}`,
      source: initId,
      target: definition.initial,
      sourceHandle: "b",
      targetHandle: "T",
      type: "transitionEdge",
      data: { isInitial: true, label: "" },
    });
  }

  return { nodes, edges };
}
