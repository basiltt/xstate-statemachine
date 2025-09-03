// src/store/slices/diagramSlice.ts

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { Node, Edge, Viewport } from "reactflow";

interface DiagramSliceState {
  // Node and edge state
  nodes: Node[];
  edges: Edge[];

  // Viewport state
  viewport: Viewport;
  initialViewport: Viewport | null;

  // Position persistence
  savedPositions: Record<string, { x: number; y: number }>;
  hasSavedPositions: boolean;

  // Layout and sizing
  autoFitAfterDrag: boolean;
  isLayouting: boolean;

  // Diagram settings
  showMinimap: boolean;

  // Active states for decoration
  activeStateIds: string[];
}

const initialState: DiagramSliceState = {
  nodes: [],
  edges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
  initialViewport: null,
  savedPositions: {},
  hasSavedPositions: false,
  autoFitAfterDrag: true,
  isLayouting: false,
  showMinimap: true,
  activeStateIds: [],
};

/**
 * Redux slice for diagram state management
 * Replaces the custom hooks for diagram state
 */
const diagramSlice = createSlice({
  name: "diagram",
  initialState,
  reducers: {
    // Node management
    setNodes: (state, action: PayloadAction<Node[]>) => {
      state.nodes = action.payload;
    },

    updateNodes: (state, action: PayloadAction<Node[]>) => {
      state.nodes = action.payload;
    },

    addNode: (state, action: PayloadAction<Node>) => {
      state.nodes.push(action.payload);
    },

    removeNode: (state, action: PayloadAction<string>) => {
      state.nodes = state.nodes.filter((node) => node.id !== action.payload);
    },

    updateNodePosition: (
      state,
      action: PayloadAction<{ id: string; position: { x: number; y: number } }>,
    ) => {
      const { id, position } = action.payload;
      const node = state.nodes.find((n) => n.id === id);
      if (node) {
        node.position = position;
      }
    },

    // Edge management
    setEdges: (state, action: PayloadAction<Edge[]>) => {
      state.edges = action.payload;
    },

    updateEdges: (state, action: PayloadAction<Edge[]>) => {
      state.edges = action.payload;
    },

    addEdge: (state, action: PayloadAction<Edge>) => {
      state.edges.push(action.payload);
    },

    removeEdge: (state, action: PayloadAction<string>) => {
      state.edges = state.edges.filter((edge) => edge.id !== action.payload);
    },

    // Viewport management
    setViewport: (state, action: PayloadAction<Viewport>) => {
      state.viewport = action.payload;
    },

    setInitialViewport: (state, action: PayloadAction<Viewport>) => {
      state.initialViewport = action.payload;
    },

    // Position persistence
    setSavedPositions: (state, action: PayloadAction<Record<string, { x: number; y: number }>>) => {
      state.savedPositions = action.payload;
      state.hasSavedPositions = Object.keys(action.payload).length > 0;
    },

    updateSavedPosition: (
      state,
      action: PayloadAction<{ nodeId: string; position: { x: number; y: number } }>,
    ) => {
      const { nodeId, position } = action.payload;
      state.savedPositions[nodeId] = position;
      state.hasSavedPositions = true;
    },

    clearSavedPositions: (state) => {
      state.savedPositions = {};
      state.hasSavedPositions = false;
    },

    // Layout management
    setAutoFitAfterDrag: (state, action: PayloadAction<boolean>) => {
      state.autoFitAfterDrag = action.payload;
    },

    setIsLayouting: (state, action: PayloadAction<boolean>) => {
      state.isLayouting = action.payload;
    },

    // Diagram settings
    setShowMinimap: (state, action: PayloadAction<boolean>) => {
      state.showMinimap = action.payload;
    },

    // Active states for decoration
    setActiveStateIds: (state, action: PayloadAction<string[]>) => {
      state.activeStateIds = action.payload;
    },

    // Bulk updates for performance
    updateDiagramState: (
      state,
      action: PayloadAction<{ nodes?: Node[]; edges?: Edge[]; viewport?: Viewport }>,
    ) => {
      const { nodes, edges, viewport } = action.payload;
      if (nodes) state.nodes = nodes;
      if (edges) state.edges = edges;
      if (viewport) state.viewport = viewport;
    },

    // Reset diagram state
    resetDiagramState: () => initialState,
  },
});

export const {
  setNodes,
  updateNodes,
  addNode,
  removeNode,
  updateNodePosition,
  setEdges,
  updateEdges,
  addEdge,
  removeEdge,
  setViewport,
  setInitialViewport,
  setSavedPositions,
  updateSavedPosition,
  clearSavedPositions,
  setAutoFitAfterDrag,
  setIsLayouting,
  setShowMinimap,
  setActiveStateIds,
  updateDiagramState,
  resetDiagramState,
} = diagramSlice.actions;

export default diagramSlice.reducer;

// Selectors
export const selectNodes = (state: { diagram: DiagramSliceState }) => state.diagram.nodes;
export const selectEdges = (state: { diagram: DiagramSliceState }) => state.diagram.edges;
export const selectViewport = (state: { diagram: DiagramSliceState }) => state.diagram.viewport;
export const selectInitialViewport = (state: { diagram: DiagramSliceState }) =>
  state.diagram.initialViewport;
export const selectSavedPositions = (state: { diagram: DiagramSliceState }) =>
  state.diagram.savedPositions;
export const selectHasSavedPositions = (state: { diagram: DiagramSliceState }) =>
  state.diagram.hasSavedPositions;
export const selectAutoFitAfterDrag = (state: { diagram: DiagramSliceState }) =>
  state.diagram.autoFitAfterDrag;
export const selectIsLayouting = (state: { diagram: DiagramSliceState }) =>
  state.diagram.isLayouting;
export const selectShowMinimap = (state: { diagram: DiagramSliceState }) =>
  state.diagram.showMinimap;
export const selectActiveStateIds = (state: { diagram: DiagramSliceState }) =>
  state.diagram.activeStateIds;
export const selectNodeById = (nodeId: string) => (state: { diagram: DiagramSliceState }) =>
  state.diagram.nodes.find((node) => node.id === nodeId);
export const selectEdgeById = (edgeId: string) => (state: { diagram: DiagramSliceState }) =>
  state.diagram.edges.find((edge) => edge.id === edgeId);
