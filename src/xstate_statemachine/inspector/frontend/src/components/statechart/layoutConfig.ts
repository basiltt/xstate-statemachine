// layoutConfig.ts

// Layout configuration similar to XState visualizer
export interface LayoutConfig {
  // ELK.js algorithm and direction
  algorithm: "layered" | "force" | "stress" | "mrtree";
  direction: "DOWN" | "UP" | "LEFT" | "RIGHT";

  // Node spacing and dimensions
  nodeWidth: number;
  nodeHeight: number;
  nodeSpacing: number; // Space between nodes on same level
  layerSpacing: number; // Space between layers/ranks
  edgeNodeSpacing: number; // Space between edges and nodes

  // Layout margins and padding
  marginX: number;
  marginY: number;
  padding: number;

  // Grid and positioning
  gridSize: number;
  snapToGrid: boolean;

  // Edge routing
  edgeRouting: "ORTHOGONAL" | "POLYLINE" | "SPLINES";

  // Compound node handling
  compoundSpacing: number;
  hierarchyHandling: "INCLUDE_CHILDREN" | "SEPARATE_CHILDREN";

  // Performance settings
  maxIterations: number;
  convergenceThreshold: number;
}

// Default configuration matching XState visualizer style
export const defaultLayoutConfig: LayoutConfig = {
  algorithm: "layered",
  // Change direction to flow from left to right
  direction: "RIGHT",

  nodeWidth: 240,
  nodeHeight: 80,
  // Increase spacing for a cleaner look
  nodeSpacing: 80,
  layerSpacing: 150,
  edgeNodeSpacing: 40,

  marginX: 100,
  marginY: 100,
  padding: 50,

  gridSize: 20,
  snapToGrid: true,

  // Set edge routing to create 90-degree angles
  edgeRouting: "ORTHOGONAL",

  compoundSpacing: 80,
  hierarchyHandling: "INCLUDE_CHILDREN",

  maxIterations: 500,
  convergenceThreshold: 0.005,
};

// Configuration for tighter layouts (when space is limited)
export const compactLayoutConfig: LayoutConfig = {
  ...defaultLayoutConfig,
  nodeSpacing: 60,
  layerSpacing: 80,
  marginX: 40,
  marginY: 40,
  padding: 20,
  compoundSpacing: 40,
};

// Configuration for wider layouts (for complex state machines)
export const expandedLayoutConfig: LayoutConfig = {
  ...defaultLayoutConfig,
  nodeSpacing: 150,
  layerSpacing: 160,
  marginX: 120,
  marginY: 120,
  padding: 60,
  compoundSpacing: 80,
};

// ELK.js specific options generator
export const generateElkOptions = (config: LayoutConfig): Record<string, any> => ({
  "elk.algorithm": config.algorithm,
  "elk.direction": config.direction,
  "elk.edgeRouting": config.edgeRouting,

  // Spacing options
  "elk.spacing.nodeNode": config.nodeSpacing.toString(),
  "elk.spacing.edgeNode": config.edgeNodeSpacing.toString(),
  "elk.layered.spacing.nodeNodeBetweenLayers": config.layerSpacing.toString(),
  "elk.layered.spacing.edgeNodeBetweenLayers": config.edgeNodeSpacing.toString(),

  // Enhanced alignment and placement
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.nodePlacement.networkSimplex.nodeFlexibility": "ALL",
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
  "elk.layered.cycleBreaking.strategy": "GREEDY",

  // Edge routing quality
  "elk.layered.edgeRouting.sloppiness": "0.1",
  "elk.layered.unnecessaryBendpoints": "false",

  // Hierarchy handling
  "elk.hierarchyHandling": config.hierarchyHandling,
  "elk.separateConnectedComponents": "false",

  // Performance
  "elk.layered.layering.strategy": "NETWORK_SIMPLEX",
  "elk.partitioning.activate": "false",

  // Port constraints for better edge connections
  "elk.portConstraints": "FIXED_SIDE",
  "elk.portAlignment.default": "CENTER",
  "elk.portAlignment.north": "CENTER",
  "elk.portAlignment.south": "CENTER",
  "elk.portAlignment.east": "CENTER",
  "elk.portAlignment.west": "CENTER",
});

// constants.ts
export const PADDING = 40; // inner padding from wrapper wall
export const ROOT_HEADER = 44; // header height
export const EDGE_CLEAR_TOP = 16; // extra air under the context block
export const GRID_SIZE = 16; // drag grid
export const GROW_PREEMPT = 40; // extra growth during drag-before-touch
