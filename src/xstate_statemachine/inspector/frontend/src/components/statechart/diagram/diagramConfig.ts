// src/config/diagramConfig.ts
import { ConnectionLineType, MarkerType } from "reactflow";

import {
  CompoundStateNode,
  EventNode,
  InitialNode,
  RootNode,
  StateNode,
} from "@/components/statechart/nodes";
import { TransitionEdge } from "@/components/statechart/edges";
import { GRID_SIZE } from "@/components/statechart/constants";

export const nodeTypes = {
  rootNode: RootNode,
  stateNode: StateNode,
  compoundStateNode: CompoundStateNode,
  eventNode: EventNode,
  initialNode: InitialNode,
};

export const edgeTypes = { transitionEdge: TransitionEdge };

export const defaultEdgeOptions = {
  type: "transitionEdge",
  markerEnd: { type: MarkerType.ArrowClosed, color: "hsl(var(--foreground))" },
};

export const proOptions = { hideAttribution: true };

export const snapGrid: [number, number] = [GRID_SIZE ?? 8, GRID_SIZE ?? 8];

export const connectionLineType = ConnectionLineType.Step;
