// statechart/layout.ts
import { Edge, MarkerType, Node } from "reactflow";
import ELK, { ElkNode } from "elkjs/lib/elk.bundled.js";
import { estimateReservedTop } from "./constants";
import { defaultLayoutConfig, generateElkOptions, LayoutConfig } from "./layoutConfig";

interface XStateNodeConfig {
  id: string;
  initial?: string;
  on?: Record<string, any>;
  states?: Record<string, XStateNodeConfig>;
  entry?: any;
  invoke?: any;
  type?: string;
}

/**
 * A helper function to recursively find a node in the ELK graph structure.
 */
function findElkNode(node: ElkNode, id: string): ElkNode | undefined {
  if (node.id === id) return node;
  if (node.children) {
    for (const child of node.children) {
      const found = findElkNode(child, id);
      if (found) return found;
    }
  }
  return undefined;
}

/**
 * The main function that takes a state machine definition and returns
 * React Flow nodes and edges with their positions calculated by ELK.js.
 */
export const getLayoutedElements = async (
  machineDef: XStateNodeConfig,
  context: Record<string, any> = {},
  config: Partial<LayoutConfig> = {},
): Promise<{ nodes: Node[]; edges: Edge[] }> => {
  const cfg: LayoutConfig = { ...defaultLayoutConfig, ...config };
  const elk = new ELK();

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const machineId = machineDef.id;
  const reservedTop = estimateReservedTop(context);

  // The ELK graph is built with a single internal "root" that contains our machine definition.
  const elkGraph: ElkNode = {
    id: "root",
    layoutOptions: generateElkOptions(cfg),
    children: [],
    edges: [],
  };

  /**
   * Recursively traverses the machine definition to build the graph structure
   * for both React Flow and the ELK layout engine.
   */
  function traverse(stateKey: string, stateDef: XStateNodeConfig, parentId?: string) {
    const stateId = parentId ? `${parentId}.${stateKey}` : stateKey;
    const isCompound = !!stateDef.states;
    const nodeType = parentId ? (isCompound ? "compoundStateNode" : "stateNode") : "rootNode";

    // 1. Create the React Flow node
    nodes.push({
      id: stateId,
      type: nodeType,
      data: { label: stateKey, definition: stateDef, machineId, ...(parentId ? {} : { context }) },
      position: { x: 0, y: 0 },
      ...(parentId && { parentId: parentId }),
    });

    // 2. Create the corresponding ELK node for layout calculation
    const elkNode: ElkNode = {
      id: stateId,
      width: cfg.nodeWidth,
      height: cfg.nodeHeight,
      children: [],
      // Add padding specifically for compound/root nodes to account for headers and spacing
      ...((isCompound || !parentId) && {
        layoutOptions: {
          "elk.padding": `[top=${cfg.padding + reservedTop},left=${cfg.padding},bottom=${cfg.padding},right=${cfg.padding}]`,
        },
      }),
    };

    // 3. Add the ELK node to its parent in the ELK graph
    const parentElkNode = parentId ? findElkNode(elkGraph, parentId) : elkGraph;
    if (parentElkNode) {
      parentElkNode.children = parentElkNode.children || [];
      parentElkNode.children.push(elkNode);
    }

    // 4. Process transitions as intermediate event nodes
    if (stateDef.on && stateDef.type !== "final") {
      for (const [event, transitionConfig] of Object.entries(stateDef.on)) {
        const configs = Array.isArray(transitionConfig) ? transitionConfig : [transitionConfig];
        for (const cfgItem of configs as any[]) {
          const targetKey: string | undefined =
            typeof cfgItem === "string" ? cfgItem : cfgItem?.target;
          if (!targetKey) continue;

          const targetParentId = parentId || machineId;
          const targetId = targetKey.startsWith(".")
            ? `${parentId}${targetKey}`
            : `${machineId}.${targetKey.replace(/^#/, `${machineId}.`)}`;
          const eventNodeId = `event-${stateId}-${targetId}-${event}`;

          nodes.push({
            id: eventNodeId,
            type: "eventNode",
            data: { label: event },
            position: { x: 0, y: 0 },
            parentId: targetParentId,
          });
          const eventElkNode: ElkNode = { id: eventNodeId, width: 120, height: 40 };

          const eventParentElkNode = findElkNode(elkGraph, targetParentId);
          if (eventParentElkNode) {
            eventParentElkNode.children = eventParentElkNode.children || [];
            eventParentElkNode.children.push(eventElkNode);
          }

          edges.push({
            id: `e-${stateId}-to-${eventNodeId}`,
            source: stateId,
            target: eventNodeId,
            type: "transitionEdge",
          });
          edges.push({
            id: `e-${eventNodeId}-to-${targetId}`,
            source: eventNodeId,
            target: targetId,
            type: "transitionEdge",
            markerEnd: { type: MarkerType.ArrowClosed, color: "hsl(var(--foreground))" },
          });
          elkGraph.edges = elkGraph.edges || [];
          elkGraph.edges.push({
            id: `elk-e-${stateId}-to-${eventNodeId}`,
            sources: [stateId],
            targets: [eventNodeId],
          });
          elkGraph.edges.push({
            id: `elk-e-${eventNodeId}-to-${targetId}`,
            sources: [eventNodeId],
            targets: [targetId],
          });
        }
      }
    }

    // 5. Handle initial state indicators
    if (stateDef.initial) {
      const initialNodeId = `${stateId}.__initial__`;
      const targetId = `${stateId}.${stateDef.initial}`;
      nodes.push({
        id: initialNodeId,
        type: "initialNode",
        position: { x: 0, y: 0 },
        parentId: stateId,
        data: { label: "" },
      });
      edges.push({
        id: `e-${initialNodeId}-${targetId}`,
        source: initialNodeId,
        target: targetId,
        type: "transitionEdge",
        data: { isInitial: true },
      });

      const initialElkNode: ElkNode = { id: initialNodeId, width: 24, height: 24 };
      const parentElk = findElkNode(elkGraph, stateId);
      if (parentElk) {
        parentElk.children = parentElk.children || [];
        parentElk.children.push(initialElkNode);
        elkGraph.edges = elkGraph.edges || [];
        elkGraph.edges.push({
          id: `elk-${initialNodeId}-${targetId}`,
          sources: [initialNodeId],
          targets: [targetId],
        });
      }
    }

    // 6. Recurse for nested states
    if (stateDef.states) {
      for (const childKey in stateDef.states) {
        traverse(childKey, stateDef.states[childKey], stateId);
      }
    }
  }

  // Start building the graph from the root of the machine definition
  traverse(machineDef.id, machineDef);

  // Run the ELK layout engine
  const layoutedGraph = await elk.layout(elkGraph);
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  /**
   * This recursive function correctly applies the calculated positions from ELK
   * to our React Flow nodes. It's crucial because ELK provides coordinates
   * relative to a node's parent, and this structure ensures that nesting is handled.
   */
  function applyPositions(elkNode: ElkNode) {
    const rfNode = nodeMap.get(elkNode.id);
    if (rfNode) {
      // Apply the position calculated by ELK.
      rfNode.position = { x: elkNode.x || 0, y: elkNode.y || 0 };
      // Apply the dimensions calculated by ELK.
      rfNode.width = elkNode.width;
      rfNode.height = elkNode.height;

      // For container nodes (like the root), we also set the size in the style
      // property, which is what React Flow uses to render the component's dimensions.
      if (rfNode.type === "rootNode" || rfNode.type === "compoundStateNode") {
        rfNode.style = { width: rfNode.width, height: rfNode.height };
      }
    }
    // Recurse for all children to handle nested states
    if (elkNode.children) {
      elkNode.children.forEach(applyPositions);
    }
  }

  // Start the position application from the top-level children of the layouted graph
  if (layoutedGraph.children) {
    layoutedGraph.children.forEach(applyPositions);
  }

  return { nodes, edges };
};
