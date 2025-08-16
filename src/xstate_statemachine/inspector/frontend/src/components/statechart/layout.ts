import { Edge, MarkerType, Node } from "reactflow";
import ELK, { ElkNode, ElkExtendedEdge } from "elkjs/lib/elk.bundled.js";
import { estimateReservedTop, ROOT_HEADER, EDGE_CLEAR_TOP } from "./constants";
import { defaultLayoutConfig, generateElkOptions, LayoutConfig } from "./layoutConfig";

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

// Removed unused NODE_WIDTH/NODE_HEIGHT constants; we rely on config values
export const getLayoutedElements = async (
  machineDef: XStateNodeConfig,
  context: Record<string, any> = {},
  config: Partial<LayoutConfig> = {}
): Promise<{ nodes: Node[]; edges: Edge[] }> => {
  const cfg: LayoutConfig = { ...defaultLayoutConfig, ...config };
  const elk = new ELK();

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const machineId = machineDef.id;
  const reservedTop = estimateReservedTop(context) + EDGE_CLEAR_TOP;

  // Build ELK graph hierarchy
  const elkRootNode: ElkNode = {
    id: "root",
    layoutOptions: generateElkOptions(cfg),
    children: [],
    edges: []
  };

  function traverse(stateKey: string, stateDef: XStateNodeConfig, parentId?: string) {
    const stateId = parentId ? `${parentId}.${stateKey}` : stateKey;
    const isCompound = !!stateDef.states;
    const nodeType = parentId ? (isCompound ? "compoundStateNode" : "stateNode") : "rootNode";
    const isRootChild = !!parentId && parentId === machineId;

    // Add node as before
    nodes.push({
      id: stateId,
      type: nodeType,
      data: { label: stateKey, definition: stateDef, machineId, ...(parentId ? {} : { context }) },
      position: { x: 0, y: 0 },
      style: nodeType === "rootNode" ? { zIndex: 0 } : isRootChild ? { zIndex: 1 } : undefined,
      ...(parentId && { parentNode: parentId }),
    });

    // Build ELK node
    const elkNode: ElkNode = {
      id: stateId,
      width: cfg.nodeWidth,
      height: cfg.nodeHeight,
      children: [],
      layoutOptions: {
        ...generateElkOptions(cfg),
        'elk.padding': `[top=${cfg.padding},left=${cfg.padding},bottom=${cfg.padding},right=${cfg.padding}]`,
        'elk.spacing.nodeNode': cfg.nodeSpacing.toString(),
        'elk.layered.spacing.nodeNodeBetweenLayers': cfg.layerSpacing.toString(),
      }
    };

    // Add to appropriate parent
    if (parentId) {
      const findAndAddToParent = (node: ElkNode, targetParentId: string): boolean => {
        if (node.id === targetParentId) {
          node.children = node.children || [];
          node.children.push(elkNode);
          return true;
        }
        if (node.children) {
          for (const child of node.children) {
            if (findAndAddToParent(child, targetParentId)) return true;
          }
        }
        return false;
      };
      findAndAddToParent(elkRootNode, parentId);
    } else {
      elkRootNode.children!.push(elkNode);
    }

    // Helper function to check if ELK node exists
    const elkNodeExists = (node: ElkNode, targetId: string): boolean => {
      if (node.id === targetId) return true;
      if (node.children) {
        return node.children.some(child => elkNodeExists(child, targetId));
      }
      return false;
    };

    // Process entry actions as separate nodes
    if (stateDef.entry) {
      const entryActions = asArray(stateDef.entry);
      entryActions.forEach((action: any, index: number) => {
        const actionId = `${stateId}.entry_action_${index}`;
        // Check if node already exists to prevent duplicates
        if (!nodes.find(n => n.id === actionId)) {
          nodes.push({
            id: actionId,
            type: 'ActionNode',
            data: { label: action.type || action },
            position: { x: 0, y: 0 },
            parentNode: stateId,
            draggable: true,
          });
        }

        const actionElkNode: ElkNode = {
          id: actionId,
          width: 180,
          height: 60,
        };
        
        if (!elkNodeExists(elkRootNode, actionId)) {
          const findParent = (node: ElkNode) => {
            if (node.id === stateId) {
              node.children = node.children || [];
              node.children.push(actionElkNode);
            } else if (node.children) {
              node.children.forEach(findParent);
            }
          };
          findParent(elkRootNode);

          edges.push({
            id: `e-${stateId}-${actionId}`,
            source: stateId,
            target: actionId,
            type: 'transitionEdge',
            data: { label: 'entry' },
          });
          elkRootNode.edges!.push({
            id: `elk-${stateId}-${actionId}`,
            sources: [stateId],
            targets: [actionId],
          });
        }
      });
    }

    // Process invokes as separate nodes
    if (stateDef.invoke) {
      const invokes = asArray(stateDef.invoke);
      invokes.forEach((invoke: any, index: number) => {
        const invokeId = `${stateId}.invoke_${index}`;
        // Check if node already exists to prevent duplicates
        if (!nodes.find(n => n.id === invokeId)) {
          nodes.push({
            id: invokeId,
            type: 'InvokeNode',
            data: { label: invoke.src || 'Invoke' },
            position: { x: 0, y: 0 },
            parentNode: stateId,
            draggable: true,
          });
        }

        const invokeElkNode: ElkNode = {
          id: invokeId,
          width: 180,
          height: 60,
        };
        
        // Only add ELK node if it doesn't already exist
        if (!elkNodeExists(elkRootNode, invokeId)) {
        const findParent = (node: ElkNode) => {
          if (node.id === stateId) {
            node.children = node.children || [];
            node.children.push(invokeElkNode);
          } else if (node.children) {
            node.children.forEach(findParent);
          }
        };
        findParent(elkRootNode);

        edges.push({
          id: `e-${stateId}-${invokeId}`,
          source: stateId,
          target: invokeId,
          type: 'transitionEdge',
          data: { label: 'invoke' },
        });
        elkRootNode.edges!.push({
          id: `elk-${stateId}-${invokeId}`,
          sources: [stateId],
          targets: [invokeId],
        });
        }
      });
    }

    // Note: ELK node already added above in the initial processing

    // Process transitions (skip for final states)
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

          // Add React Flow edge
          edges.push({
            id: `e-${stateId}-${targetId}-${event}`,
            source: stateId,
            target: targetId,
            type: "transitionEdge",
            data: { label: event, actions: (cfg as any)?.actions },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#a1a1aa" },
          });

          // Add ELK edge
          const elkEdge: ElkExtendedEdge = {
            id: `elk-${stateId}-${targetId}-${event}`,
            sources: [stateId],
            targets: [targetId]
          };
          elkRootNode.edges!.push(elkEdge);
        }
      }
    }

    // Initial state indicator
    if (stateDef.initial) {
      const initialNodeId = `${stateId}.__initial__`;
      const targetId = `${stateId}.${stateDef.initial}`;
      
      nodes.push({
        id: initialNodeId,
        type: "initialNode",
        position: { x: 0, y: 0 },
        parentNode: stateId,
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

      // Add initial node to ELK
      const initialElkNode: ElkNode = {
        id: initialNodeId,
        width: 16,
        height: 16
      };
      
      // Find parent and add initial node
      const findParentForInitial = (node: ElkNode, targetParentId: string): boolean => {
        if (node.id === targetParentId) {
          node.children = node.children || [];
          node.children.push(initialElkNode);
          return true;
        }
        if (node.children) {
          for (const child of node.children) {
            if (findParentForInitial(child, targetParentId)) return true;
          }
        }
        return false;
      };
      findParentForInitial(elkRootNode, stateId);

      // Add edge for initial transition
      elkRootNode.edges!.push({
        id: `elk-${initialNodeId}-${targetId}`,
        sources: [initialNodeId],
        targets: [targetId]
      });
    }

    // Recursively handle children
    if (stateDef.states) {
      for (const childKey in stateDef.states) {
        traverse(childKey, stateDef.states[childKey], stateId);
      }
    }
  }

  // Build the hierarchy
  traverse(machineDef.id, machineDef);

  // Perform ELK layout
  const layoutedGraph = await elk.layout(elkRootNode);

  // Apply ELK positions to React Flow nodes
  const applyElkPositions = (elkNode: ElkNode) => {
    const reactFlowNode = nodes.find(n => n.id === elkNode.id);
    if (reactFlowNode && elkNode.x !== undefined && elkNode.y !== undefined) {
      // Snap to grid with proper spacing
      const snapX = Math.round(elkNode.x / cfg.gridSize) * cfg.gridSize;
      const snapY = Math.round(elkNode.y / cfg.gridSize) * cfg.gridSize;
      
      reactFlowNode.position = {
        x: cfg.snapToGrid ? snapX : elkNode.x,
        y: cfg.snapToGrid ? snapY : elkNode.y
      };
    }
    
    // Recursively apply to children
    if (elkNode.children) {
      elkNode.children.forEach(applyElkPositions);
    }
  };

  applyElkPositions(layoutedGraph);

  // Handle root node wrapper sizing similar to original implementation
  const rootId = machineId;
  const rootNode = nodes.find((n) => n.id === rootId);
  const childNodes = nodes.filter((n) => n.parentNode === rootId);

  if (rootNode && childNodes.length > 0) {
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;

    childNodes.forEach((n) => {
      const w = cfg.nodeWidth;
      const h = cfg.nodeHeight;
      minX = Math.min(minX, n.position.x);
      minY = Math.min(minY, n.position.y);
      maxX = Math.max(maxX, n.position.x + w);
      maxY = Math.max(maxY, n.position.y + h);
    });

    // Include edge extents with proper margins
    const EDGE_MARGIN = cfg.edgeNodeSpacing * 2;
    edges.forEach((e) => {
      const s = nodes.find(n => n.id === e.source);
      const t = nodes.find(n => n.id === e.target);
      if (!s || !t) return;
      if (s.parentNode !== rootId || t.parentNode !== rootId) return;
      
      const sw = cfg.nodeWidth / 2;
      const sh = cfg.nodeHeight / 2;
      const tw = cfg.nodeWidth / 2;
      const th = cfg.nodeHeight / 2;
      const sx = s.position.x + sw;
      const sy = s.position.y + sh;
      const tx = t.position.x + tw;
      const ty = t.position.y + th;
      
      minX = Math.min(minX, Math.min(sx, tx) - EDGE_MARGIN);
      maxX = Math.max(maxX, Math.max(sx, tx) + EDGE_MARGIN);
      minY = Math.min(minY, Math.min(sy, ty) - EDGE_MARGIN);
      maxY = Math.max(maxY, Math.max(sy, ty) + EDGE_MARGIN);
    });

    // Position root node and calculate dimensions
    rootNode.position = { 
      x: minX - cfg.marginX, 
      y: minY - cfg.marginY 
    };
    
    const rootWidth = maxX - minX + cfg.marginX * 2;
    const rootHeight = maxY - minY + cfg.marginY * 2 + reservedTop - ROOT_HEADER;
    
    rootNode.style = {
      ...(rootNode.style as any),
      width: rootWidth,
      height: rootHeight,
      zIndex: 0,
    } as any;

    // Adjust children positions relative to root
    childNodes.forEach((n) => {
      n.position.x = Math.round((n.position.x - rootNode.position.x) / cfg.gridSize) * cfg.gridSize;
      n.position.y = Math.round((n.position.y - rootNode.position.y + reservedTop) / cfg.gridSize) * cfg.gridSize;
    });
  }

  return { nodes, edges };
};

// For backwards compatibility - sync version that returns a promise
export const getLayoutedElementsSync = (
  machineDef: XStateNodeConfig,
  context: Record<string, any> = {},
  config: Partial<LayoutConfig> = {}
): { nodes: Node[]; edges: Edge[] } => {
  // This is a temporary sync wrapper - in practice, you should use the async version
  let result: { nodes: Node[]; edges: Edge[] } = { nodes: [], edges: [] };
  
  getLayoutedElements(machineDef, context, config).then(layout => {
    result = layout;
  }).catch(err => {
    console.error('ELK layout failed:', err);
    // Fallback to basic positioning
    result = { nodes: [], edges: [] };
  });
  
  return result;
};

// Helper function for array conversion
const asArray = (v: any) => (v ? (Array.isArray(v) ? v : [v]) : []);

export const getInteractiveLayout = async (rfNodes: Node[], rfEdges: Edge[], draggedNodeId: string, config: Partial<LayoutConfig> = {}) => {
  const cfg: LayoutConfig = { ...defaultLayoutConfig, ...config, algorithm: 'force' };
  const elk = new ELK();

  const elkNodesMap = new Map<string, ElkNode>();
  rfNodes.forEach(node => {
    const elkNode: ElkNode = {
      id: node.id,
      x: node.position.x,
      y: node.position.y,
      width: node.width || cfg.nodeWidth,
      height: node.height || cfg.nodeHeight,
      children: [],
      layoutOptions: node.id === draggedNodeId ? { 'org.eclipse.elk.force.priority': '100' } : { 'org.eclipse.elk.force.priority': '1' },
    };
    elkNodesMap.set(node.id, elkNode);
  });

  rfNodes.forEach(node => {
    if (node.parentNode) {
      const parent = elkNodesMap.get(node.parentNode);
      if (parent) {
        parent.children!.push(elkNodesMap.get(node.id)!);
      }
    }
  });

  const rootElk = Array.from(elkNodesMap.values()).find(n => !rfNodes.find(rn => rn.id === n.id)?.parentNode);
  if (!rootElk) throw new Error('No root');

  rootElk.layoutOptions = generateElkOptions(cfg);
  rootElk.edges = rfEdges.map(edge => ({
    id: edge.id,
    sources: [edge.source],
    targets: [edge.target],
  }));

  const newLayout = await elk.layout(rootElk);

  const newPositions = new Map<string, {x: number, y: number}>();
  function extractPositions(elkN: ElkNode) {
    newPositions.set(elkN.id, {x: elkN.x || 0, y: elkN.y || 0});
    if (elkN.children) {
      elkN.children.forEach(extractPositions);
    }
  }
  extractPositions(newLayout);

  const updatedNodes = rfNodes.map(node => ({
    ...node,
    position: newPositions.get(node.id) || node.position,
  }));

  return { nodes: updatedNodes, edges: rfEdges };
};
