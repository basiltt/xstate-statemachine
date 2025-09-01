import type { Edge, Node } from "reactflow";
import { EDGE_CLEAR_TOP, estimateReservedTop, GRID_SIZE, PADDING, ROOT_HEADER } from "./constants";

/* ──────────────────────────────────────────────────────────────────────────
   Size & spacing (visual hints; RF will measure true node sizes at runtime)
   ────────────────────────────────────────────────────────────────────────── */
const STATE_W = 260;
const STATE_H_HINT = 140;
const COL_GAP = 180;
const ROW_GAP = 100;

const INNER_PAD_X = (PADDING ?? 40) + 64;
const INNER_PAD_Y = (PADDING ?? 40) + 56;

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
type TEdge = { source: string; target: string; label?: string };

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
   Layered (left→right) layout, tolerant to cycles
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

  // simple barycenter pass to reduce crossings
  const idx = new Map<string, number>();
  layers.forEach((col, i) => col.forEach((id) => idx.set(id, i)));
  for (let i = 1; i < layers.length; i++) {
    const incoming: Record<string, number[]> = {};
    for (const e of edges) {
      if (idx.get(e.target) === i && idx.get(e.source) === i - 1) {
        (incoming[e.target] ||= []).push(layers[i - 1].indexOf(e.source));
      }
    }
    const mean = (xs: number[]) => (xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : 0);
    layers[i].sort((a, b) => mean(incoming[a] ?? []) - mean(incoming[b] ?? []));
  }
  return layers;
}

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

/* ──────────────────────────────────────────────────────────────────────────
   Public API
   ────────────────────────────────────────────────────────────────────────── */
export async function getLayoutedElements(
  definition: MachineDef | undefined,
  context: Record<string, any> | undefined | null,
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  // Defensive: always give back at least a root wrapper
  const machineId = definition?.id ?? "StateMachine";
  const rootId = `${machineId}__root`;

  if (!definition || !definition.states || Object.keys(definition.states).length === 0) {
    return {
      nodes: [
        {
          id: rootId,
          type: "rootNode",
          data: { label: machineId, context: context ?? {} },
          position: { x: GRID_SIZE ?? 8, y: GRID_SIZE ?? 8 },
          style: { width: 980, height: 560 },
          draggable: true,
          selectable: false,
        },
      ],
      edges: [],
    };
  }

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

  const sPos = positionStates(layers, reservedTop);

  // wrapper size hints
  const cols = Math.max(1, layers.length);
  const widthHint = Math.max(980, INNER_PAD_X * 2 + cols * STATE_W + (cols - 1) * COL_GAP);
  const tallest = Math.max(
    ...layers.map((col) => col.length * STATE_H_HINT + Math.max(0, col.length - 1) * ROW_GAP),
    STATE_H_HINT,
  );
  const heightHint = Math.max(560, reservedTop + INNER_PAD_Y * 2 + tallest);

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

  for (const s of states) {
    const p = sPos[s.id] ?? { x: INNER_PAD_X, y: reservedTop + INNER_PAD_Y };
    nodes.push({
      id: s.id,
      type: s.def?.states ? "compoundStateNode" : "stateNode",
      data: { label: s.key, definition: s.def, machineId, headerOnly: !hasBody(s.def) },
      position: p,
      style: { width: STATE_W }, // RF measures height from component
      parentId: rootId,
      extent: "parent",
      draggable: true,
    });
  }

  const edges: Edge[] = transitions.map((t, i) => ({
    id: `t_${i}_${t.source}__${t.target}`,
    type: "transitionEdge",
    source: t.source,
    target: t.target,
    data: { label: t.label },
  }));

  return { nodes, edges };
}
