import { create } from "zustand";
import { useEffect } from "react";

// --- START: Explicit Type Definitions ---
export interface LogEntry {
  type: string;
  payload: any;
  timestamp?: string;
  machine_id?: string;
}

export interface MachineState {
  id: string;
  definition: any;
  currentStateIds: string[];
  context: any;
  logs: LogEntry[];
  services: Record<string, { src: string; status: string }>;
}

interface InspectorState {
  machines: Record<string, MachineState>;
  addMachine: (data: any) => void;
  updateMachineTransition: (data: any) => void;
  addService: (data: any) => void;
  removeService: (data: any) => void;
  addLog: (machineId: string, log: LogEntry) => void;
}

// --- END: Explicit Type Definitions ---

export const useInspectorStore = create<InspectorState>((set) => ({
  machines: {},
  addMachine: (data) =>
    set((state) => ({
      machines: {
        ...state.machines,
        [data.machine_id]: {
          id: data.machine_id,
          definition: data.definition,
          currentStateIds: data.initial_state_ids,
          context: data.initial_context,
          logs: [{ type: "machine_registered", payload: data }],
          services: {},
        },
      },
    })),
  updateMachineTransition: (data) =>
    set((state) => {
      if (!state.machines[data.machine_id]) return state;
      return {
        machines: {
          ...state.machines,
          [data.machine_id]: {
            ...state.machines[data.machine_id],
            currentStateIds: data.to_state_ids,
            context: data.full_context,
            logs: [...state.machines[data.machine_id].logs, { type: "transition", payload: data }],
          },
        },
      };
    }),
  addService: (data) =>
    set((state) => {
      if (!state.machines[data.machine_id]) return state;
      return {
        machines: {
          ...state.machines,
          [data.machine_id]: {
            ...state.machines[data.machine_id],
            services: {
              ...state.machines[data.machine_id].services,
              [data.id]: { src: data.service, status: "running" },
            },
            logs: [
              ...state.machines[data.machine_id].logs,
              { type: "service_invoked", payload: data },
            ],
          },
        },
      };
    }),
  removeService: (data) =>
    set((state) => {
      if (!state.machines[data.machine_id]) return state;
      const newServices = { ...state.machines[data.machine_id].services };
      delete newServices[data.id];
      return {
        machines: {
          ...state.machines,
          [data.machine_id]: {
            ...state.machines[data.machine_id],
            services: newServices,
          },
        },
      };
    }),
  addLog: (machineId, log) =>
    set((state) => {
      if (!state.machines[machineId]) return state;
      return {
        machines: {
          ...state.machines,
          [machineId]: {
            ...state.machines[machineId],
            logs: [...state.machines[machineId].logs, log],
          },
        },
      };
    }),
}));

export const useInspectorSocket = () => {
  const {
    addMachine,
    updateMachineTransition,
    addService,
    removeService,
    addLog,
  } = useInspectorStore();

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8008/ws");

    ws.onopen = () => console.log("Inspector WebSocket connected");
    ws.onclose = () => console.log("Inspector WebSocket disconnected");
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "machine_registered":
          addMachine(msg.payload);
          break;
        case "transition":
          updateMachineTransition(msg.payload);
          break;
        case "service_invoked":
          addService(msg.payload);
          break;
        case "service_stopped":
          removeService(msg.payload);
          break;
        default:
          // Handle all other events as generic logs
          addLog(msg.machine_id, { type: msg.type, payload: msg.payload, ...msg });
          break;
      }
    };

    return () => {
      ws.close();
    };
  }, [addMachine, updateMachineTransition, addService, removeService, addLog]);
};
