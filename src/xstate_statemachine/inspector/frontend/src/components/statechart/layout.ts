import { Edge, MarkerType, Node } from "reactflow";
import dagre from "dagre";
import { estimateReservedTop, PADDING, ROOT_HEADER, EDGE_CLEAR_TOP, GRID_SIZE } from "./constants";

// --- Type Definitions ---
interface XStateNodeConfig {
  id: string;
  initial?: string;
  on?: Record<string, any>;
  states?: Record<string, XStateNodeConfig>;
  entry?: any;
  invoke?: any;
  type?: string; // allow checking for final state
}

const NODE_WIDTH = 260;
const NODE_HEIGHT = 80;

export const getLayoutedElements = (
  machineDef: XStateNodeConfig,
  context: Record<string, any> = {},
): { nodes: Node[]; edges: Edge[] } => {
  // Fresh graph each time to avoid accumulating old nodes/edges
  const dagreGraph = new dagre.graphlib.Graph({ compound: true });
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: "TB", nodesep: 120, ranksep: 120, marginx: 40, marginy: 40 });

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const machineId = machineDef.id;
  const reservedTop = estimateReservedTop(context) + EDGE_CLEAR_TOP;

  function traverse(stateKey: string, stateDef: XStateNodeConfig, parentId?: string) {
    const stateId = parentId ? `${parentId}.${stateKey}` : stateKey;
    const isCompound = !!stateDef.states;
    const nodeType = parentId ? (isCompound ? "compoundStateNode" : "stateNode") : "rootNode";
    const isRootChild = !!parentId && parentId === machineId;

    nodes.push({
      id: stateId,
      type: nodeType,
      data: { label: stateKey, definition: stateDef, machineId, ...(parentId ? {} : { context }) },
      position: { x: 0, y: 0 },
      style: nodeType === "rootNode" ? { zIndex: 0 } : isRootChild ? { zIndex: 1 } : undefined,
      // keep grouping under parent, but DO NOT constrain dragging to parent extent
      ...(parentId && { parentNode: parentId }),
    });

    dagreGraph.setNode(stateId, { width: NODE_WIDTH, height: NODE_HEIGHT });
    if (parentId) dagreGraph.setParent(stateId, parentId);

    // Transitions (skip for final states)
    if (stateDef.on && stateDef.type !== "final") {
      for (const [event, transitionConfig] of Object.entries(stateDef.on)) {
        const configs = Array.isArray(transitionConfig) ? transitionConfig : [transitionConfig];
        for (const cfg of configs as any[]) {
          const targetKey: string | undefined =
            typeof cfg === "string" ? (cfg as string) : (cfg?.target as string | undefined);
          if (!targetKey) continue;
          const targetId = targetKey.startsWith(".")
            ? parentId
              ? parentId + targetKey
              : targetKey.replace(/^\./, `${stateId}.`)
            : `${machineId}${targetKey.startsWith("#") ? "" : "."}${targetKey.replace("#", "")}`;
          edges.push({
            id: `e-${stateId}-${targetId}-${event}`,
            source: stateId,
            target: targetId,
            type: "transitionEdge",
            data: { label: event, actions: (cfg as any)?.actions },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#a1a1aa" },
          });
          dagreGraph.setEdge(stateId, targetId);
        }
      }
    }

    // Initial indicator (for both root and nested compound states)
    if (stateDef.initial) {
      const initialNodeId = `${stateId}.__initial__`;
      const targetId = `${stateId}.${stateDef.initial}`;
      nodes.push({
        id: initialNodeId,
        type: "initialNode",
        position: { x: 0, y: 0 },
        parentNode: stateId, // keep inside wrapper grouping only
        data: { label: "" },
        style: isRootChild || !parentId ? { zIndex: 1 } : undefined,
      });
      edges.push({
        id: `e-${initialNodeId}-${targetId}`,
        source: initialNodeId,
        target: targetId,
        type: "transitionEdge",
        data: { label: "" },
      });
      dagreGraph.setNode(initialNodeId, { width: 16, height: 16 });
      dagreGraph.setEdge(initialNodeId, targetId);
    }

    if (stateDef.states) {
      for (const childKey in stateDef.states)
        traverse(childKey, stateDef.states[childKey], stateId);
    }
  }

  traverse(machineDef.id, machineDef);
  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const d = dagreGraph.node(node.id);
    if (d) {
      // snap dagre to grid
      const sx = Math.round((d.x - d.width / 2) / GRID_SIZE) * GRID_SIZE;
      const sy = Math.round((d.y - d.height / 2) / GRID_SIZE) * GRID_SIZE;
      node.position = { x: sx, y: sy };
    }
  });

  // Wrap children inside the root with padding + reserved top area
  const rootId = machineId;
  const rootNode = nodes.find((n) => n.id === rootId);
  const childNodes = nodes.filter((n) => n.parentNode === rootId);

  if (rootNode && childNodes.length > 0) {
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    const idToNode = new Map(nodes.map((n) => [n.id, n] as const));

    childNodes.forEach((n) => {
      const d = dagreGraph.node(n.id);
      const w = d?.width ?? NODE_WIDTH;
      const h = d?.height ?? NODE_HEIGHT;
      minX = Math.min(minX, n.position.x);
      minY = Math.min(minY, n.position.y);
      maxX = Math.max(maxX, n.position.x + w);
      maxY = Math.max(maxY, n.position.y + h);
    });

    // include internal edge extents
    const EDGE_MARGIN = 32;
    edges.forEach((e) => {
      const s = idToNode.get(e.source);
      const t = idToNode.get(e.target);
      if (!s || !t) return;
      if (s.parentNode !== rootId || t.parentNode !== rootId) return;
      const ds = dagreGraph.node(s.id);
      const dt = dagreGraph.node(t.id);
      const sw = (ds?.width ?? NODE_WIDTH) / 2;
      const sh = (ds?.height ?? NODE_HEIGHT) / 2;
      const tw = (dt?.width ?? NODE_WIDTH) / 2;
      const th = (dt?.height ?? NODE_HEIGHT) / 2;
      const sx = s.position.x + sw;
      const sy = s.position.y + sh;
      const tx = t.position.x + tw;
      const ty = t.position.y + th;
      minX = Math.min(minX, Math.min(sx, tx) - EDGE_MARGIN);
      maxX = Math.max(maxX, Math.max(sx, tx) + EDGE_MARGIN);
      minY = Math.min(minY, Math.min(sy, ty) - EDGE_MARGIN);
      maxY = Math.max(maxY, Math.max(sy, ty) + EDGE_MARGIN);
    });

    rootNode.position = { x: minX - PADDING / 2, y: minY - PADDING / 2 };
    const rootWidth = maxX - minX + PADDING;
    const rootHeight = maxY - minY + PADDING + reservedTop - ROOT_HEADER;
    rootNode.style = {
      ...(rootNode.style as any),
      width: rootWidth,
      height: rootHeight,
      zIndex: 0,
    } as any;

    // shift children relative to root and push down under header/context
    childNodes.forEach((n) => {
      n.position.x = Math.round((n.position.x - rootNode.position.x) / GRID_SIZE) * GRID_SIZE;
      n.position.y =
        Math.round((n.position.y - rootNode.position.y + reservedTop) / GRID_SIZE) * GRID_SIZE;
    });

    // Clamp to keep inside, and resolve simple overlaps by nudging on the grid
    const leftBound = Math.ceil(PADDING / 2 / GRID_SIZE) * GRID_SIZE;
    const topBound = Math.ceil(reservedTop / GRID_SIZE) * GRID_SIZE;
    const rightBound = Math.floor((rootWidth - PADDING / 2) / GRID_SIZE) * GRID_SIZE;
    const bottomBound = Math.floor((rootHeight - PADDING / 2) / GRID_SIZE) * GRID_SIZE;

    const rects: Array<{ id: string; x: number; y: number; w: number; h: number }> = [];

    for (const n of childNodes) {
      const d = dagreGraph.node(n.id);
      const w = Math.ceil((d?.width ?? NODE_WIDTH) / GRID_SIZE) * GRID_SIZE;
      const h = Math.ceil((d?.height ?? NODE_HEIGHT) / GRID_SIZE) * GRID_SIZE;
      let x = Math.min(Math.max(n.position.x, leftBound), rightBound - w);
      let y = Math.min(Math.max(n.position.y, topBound), bottomBound - h);

      // nudge to avoid overlaps
      const collides = (ax: number, ay: number) =>
        rects.some(
          ({ x: bx, y: by, w: bw, h: bh }) =>
            ax < bx + bw && ax + w > bx && ay < by + bh && ay + h > by,
        );

      let attempts = 0;
      while (collides(x, y) && attempts < 500) {
        x += GRID_SIZE;
        if (x + w > rightBound) {
          x = leftBound;
          y += GRID_SIZE;
          if (y + h > bottomBound) break;
        }
        attempts++;
      }

      n.position.x = x;
      n.position.y = y;
      rects.push({ id: n.id, x, y, w, h });
    }
  }

  return { nodes, edges };
};
