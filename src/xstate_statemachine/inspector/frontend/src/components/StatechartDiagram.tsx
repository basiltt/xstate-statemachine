import { useMemo } from "react";
import ReactFlow, { MiniMap, Controls, Background, Node, Edge, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import * as dagre from "dagre";

// --- START: Type Definitions for a Type-Safe Component ---

// FIX: A new, comprehensive type for all valid XState transition formats
type TransitionObject = { target: string };
type TransitionConfig = string | TransitionObject | (string | TransitionObject)[];

interface XStateNode {
  id: string;
  key: string;
  initial?: string;
  on?: Record<string, TransitionConfig>;
  states?: Record<string, XStateNode>;
}

interface MachineDefinition {
  id: string;
  initial?: string;
  states: Record<string, XStateNode>;
}

// --- END: Type Definitions ---

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 200;
const nodeHeight = 50;

const getLayoutedElements = (
  machine: MachineDefinition,
  activeStateIds: string[]
): { nodes: Node[]; edges: Edge[] } => {
  dagreGraph.setGraph({ rankdir: "TB", nodesep: 25, ranksep: 60 });

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  function traverse(stateNode: XStateNode) {
    if (!stateNode || !stateNode.id) return;

    nodes.push({
      id: stateNode.id,
      data: { label: stateNode.key },
      position: { x: 0, y: 0 },
      style: {
        background: activeStateIds.includes(stateNode.id) ? "#3b82f6" : "#ffffff",
        color: activeStateIds.includes(stateNode.id) ? "white" : "black",
        border: "1px solid #9ca3af",
        borderRadius: "8px",
        width: nodeWidth,
        height: nodeHeight,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      },
    });
    dagreGraph.setNode(stateNode.id, { width: nodeWidth, height: nodeHeight });

    if (stateNode.on) {
      for (const event in stateNode.on) {
        // FIX: Provide an explicit type annotation to resolve TS7022
        const transitionConfig: TransitionConfig = stateNode.on[event];

        // Normalize to an array to handle all cases (string, object, array)
        const transitions = Array.isArray(transitionConfig) ? transitionConfig : [transitionConfig];

        for (const transition of transitions) {
          const targetKey = typeof transition === "string" ? transition : transition.target;

          // This is a simplified target resolution logic for visualization
          const targetId = targetKey.startsWith(".")
            ? stateNode.id.substring(0, stateNode.id.lastIndexOf(".")) + targetKey
            : `${machine.id}.${targetKey}`;

          edges.push({
            id: `e-${stateNode.id}-${targetId}-${event}`,
            source: stateNode.id,
            target: targetId,
            label: event,
            markerEnd: { type: MarkerType.ArrowClosed },
          });
          dagreGraph.setEdge(stateNode.id, targetId);
        }
      }
    }

    if (stateNode.states) {
      for (const key in stateNode.states) {
        const childState = stateNode.states[key];
        childState.id = `${stateNode.id}.${key}`;
        childState.key = key;
        traverse(childState);
      }
    }
  }

  const rootNode = { ...machine, id: machine.id, key: machine.id };
  traverse(rootNode);

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    if (nodeWithPosition) {
      node.position = {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      };
    }
  });

  return { nodes, edges };
};

interface StatechartDiagramProps {
  machine: { definition: MachineDefinition };
  activeStateIds: string[];
}

export const StatechartDiagram = ({ machine, activeStateIds }: StatechartDiagramProps) => {
  const { nodes, edges } = useMemo(() => getLayoutedElements(machine.definition, activeStateIds), [
    machine.definition,
    activeStateIds,
  ]);

  if (!nodes || nodes.length === 0) {
    return <div className="p-4 text-gray-500">Could not render diagram.</div>;
  }

  return (
    <div className="h-[600px] w-full bg-gray-50 dark:bg-gray-900 rounded-lg border dark:border-gray-700">
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Controls />
        <MiniMap nodeStrokeWidth={3} zoomable pannable />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
};
