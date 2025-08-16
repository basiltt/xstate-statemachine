import { Edge, MarkerType, Node } from "reactflow";
import * as dagre from "dagre";

// --- Type Definitions ---
interface XStateNodeConfig {
  id: string;
  initial?: string;
  on?: Record<string, any>;
  states?: Record<string, XStateNodeConfig>;
  entry?: any;
  invoke?: any;
}

// --- Dagre Layout Setup ---
const dagreGraph = new dagre.graphlib.Graph({ compound: true });
dagreGraph.setDefaultEdgeLabel(() => ({}));
dagreGraph.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 60 });

const nodeWidth = 250;
const nodeHeight = 60;

export const getLayoutedElements = (
  machineDef: XStateNodeConfig,
  context: Record<string, any> = {},
): { nodes: Node[]; edges: Edge[] } => {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const machineId = machineDef.id;

  function traverse(stateKey: string, stateDef: XStateNodeConfig, parentId?: string) {
    const stateId = parentId ? `${parentId}.${stateKey}` : stateKey;
    const isCompound = !!stateDef.states;

    const nodeType = parentId ? (isCompound ? "compoundStateNode" : "stateNode") : "rootNode";

    nodes.push({
      id: stateId,
      type: nodeType,
      data: {
        label: stateKey,
        definition: stateDef,
        machineId,
        ...(parentId ? {} : { context }),
      },
      position: { x: 0, y: 0 },
      ...(parentId && { parentNode: parentId, extent: "parent" }),
    });

    dagreGraph.setNode(stateId, { width: nodeWidth, height: nodeHeight });
    if (parentId) {
      dagreGraph.setParent(stateId, parentId);
    }

    if (stateDef.on) {
      const transitions = Array.isArray(stateDef.on) ? stateDef.on : Object.entries(stateDef.on);
      for (const [event, transitionConfig] of transitions) {
        const configs = Array.isArray(transitionConfig) ? transitionConfig : [transitionConfig];
        for (const config of configs) {
          const targetKey = typeof config === "string" ? config : config.target;
          if (targetKey) {
            const targetId = targetKey.startsWith(".")
              ? parentId + targetKey
              : `${machineId}${targetKey.startsWith("#") ? "" : "."}${targetKey.replace("#", "")}`;

            edges.push({
              id: `e-${stateId}-${targetId}-${event}`,
              source: stateId,
              target: targetId,
              type: "transitionEdge",
              data: { label: event, actions: config.actions },
              markerEnd: { type: MarkerType.ArrowClosed, color: "#a1a1aa" },
            });
            dagreGraph.setEdge(stateId, targetId);
          }
        }
      }
    }

    if (stateDef.initial) {
      const initialNodeId = `${stateId}.__initial__`;
      const targetId = `${stateId}.${stateDef.initial}`;
      nodes.push({
        id: initialNodeId,
        type: "initialNode",
        position: { x: 0, y: 0 },
        parentNode: stateId,
        data: { label: "" },
      });
      edges.push({
        id: `e-${initialNodeId}-${targetId}`,
        source: initialNodeId,
        target: targetId,
        type: "transitionEdge",
        data: { label: "" },
      });
      dagreGraph.setNode(initialNodeId, { width: 24, height: 24 });
      dagreGraph.setEdge(initialNodeId, targetId);
    }

    if (stateDef.states) {
      for (const childKey in stateDef.states) {
        traverse(childKey, stateDef.states[childKey], stateId);
      }
    }
  }

  traverse(machineDef.id, machineDef);
  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    if (nodeWithPosition) {
      node.position = {
        x: nodeWithPosition.x - nodeWithPosition.width / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      };
    }
  });

  // Resize root node to wrap children with padding
  const rootId = machineId;
  const padding = 40;
  const rootNode = nodes.find((n) => n.id === rootId);
  const childNodes = nodes.filter((n) => n.parentNode === rootId);

  if (rootNode && childNodes.length > 0) {
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    childNodes.forEach((n) => {
      const dim = dagreGraph.node(n.id);
      const width = dim?.width ?? nodeWidth;
      const height = dim?.height ?? nodeHeight;
      minX = Math.min(minX, n.position.x);
      minY = Math.min(minY, n.position.y);
      maxX = Math.max(maxX, n.position.x + width);
      maxY = Math.max(maxY, n.position.y + height);
    });

    rootNode.position = { x: minX - padding / 2, y: minY - padding / 2 };
    rootNode.style = {
      width: maxX - minX + padding,
      height: maxY - minY + padding,
    } as any;

    childNodes.forEach((n) => {
      n.position.x -= rootNode.position.x;
      n.position.y -= rootNode.position.y;
    });
  }

  return { nodes, edges };
};
