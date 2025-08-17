import { useCallback } from "react";
import type { Edge, Node } from "reactflow";

export function useStatusDecorators(activeStateIds: string[]) {
  const decorateStatuses = useCallback(
    (list: Node[], eds: Edge[]): Node[] => {
      const activeSet = new Set(activeStateIds);
      const nextSet = new Set<string>();
      for (const e of eds) if (activeSet.has(e.source)) nextSet.add(e.target);
      return list.map((n) => ({
        ...n,
        data: {
          ...n.data,
          uiStatus: activeSet.has(n.id) ? "active" : nextSet.has(n.id) ? "next" : undefined,
        },
      }));
    },
    [activeStateIds],
  );

  const decorateEdgeStatuses = useCallback(
    (eds: Edge[]): Edge[] => {
      const activeSet = new Set(activeStateIds);
      const nextSet = new Set<string>();
      for (const e of eds) if (activeSet.has(e.source)) nextSet.add(e.target);

      return eds.map((e) => ({
        ...e,
        data: {
          ...(e.data ?? {}),
          uiActive: activeSet.has(e.source) || nextSet.has(e.source),
        },
      }));
    },
    [activeStateIds],
  );

  return { decorateStatuses, decorateEdgeStatuses };
}
