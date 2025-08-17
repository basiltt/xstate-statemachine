// src/xstate_statemachine/inspector/frontend/src/components/statechart/constants.ts

// Shared layout and styling constants for the statechart wrapper
export const PADDING = 40; // inner padding inside wrapper
export const ROOT_HEADER = 44; // header height (px)
// Increase extra clearance under context to keep edges away a bit more
export const EDGE_CLEAR_TOP = 16; // extra top clearance under context to keep edges away
export const GRID_SIZE = 16; // snap-to-grid size for nodes and layout
// Grow the wrapper earlier so padding stays consistent while dragging
export const GROW_PREEMPT = 40;
// Margin to give edges some breathing room when calculating bounds
export const EDGE_MARGIN = 96; // was 48; larger to keep step edges fully inside wrapper

// React Flow: when a child node uses `expandParent: true`, the parent grows only while dragging
// We keep wrapper measurements reactive via guardHeaderAndMaybeGrow / fitRootTightly.

// Estimate the reserved top (header + context block height) so children and edges
// don’t overlap it. Keep this heuristic conservative but not overly large.
export function estimateReservedTop(context: Record<string, any> | undefined | null): number {
  const keys = context ? Object.keys(context) : [];
  if (!keys.length) return ROOT_HEADER; // only header
  const title = 12; // "Context" subtitle height
  const line = 12; // per-line height
  const gap = 2; // spacing below subtitle
  return ROOT_HEADER + title + gap + keys.length * line;
}

// Calculate the minimum top position for nodes to avoid the header
export function headerGuardTop(reservedTop: number): number {
  return reservedTop + PADDING / 2;
}
