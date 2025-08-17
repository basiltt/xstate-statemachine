// src/xstate_statemachine/inspector/frontend/src/hooks/useInspectorSocket.ts

import { create } from "zustand";
import { useEffect } from "react";

// --- Type Definitions for the Application State ---
// These are exported so other components, like App.tsx, can use them for props.

export interface LogEntry {
  type: string;
  payload: any;
  timestamp?: string;
  machine_id?: string;
}

export interface MachineState {
  id: string;
  definition: any; // The raw XState JSON definition
  currentStateIds: string[];
  context: any;
  logs: LogEntry[];
  services: Record<string, { src: string; status: string }>;
  lastTransition: { sourceId: string; targetId: string; event: string } | null;
}

interface InspectorState {
  ws: WebSocket | null;
  isConnected: boolean;
  machines: Record<string, MachineState>;
  connect: () => void;
  sendCommand: (command: string, payload?: object) => void;
  addMachine: (data: any) => void;
  updateMachineTransition: (data: any) => void;
  clearLastTransition: (machineId: string) => void;
  addService: (data: any) => void;
  removeService: (data: any) => void;
  addLog: (machineId: string, log: LogEntry) => void;
}

// --- Zustand State Management Store ---

export const useInspectorStore = create<InspectorState>((set, get) => ({
  // --- Initial State ---
  ws: null,
  isConnected: false,
  machines: {},

  // --- Actions ---

  // Action to initialize and manage the WebSocket connection
  connect: () => {
    if (get().ws) return; // Prevent multiple connections

    const ws = new WebSocket("ws://127.0.0.1:8008/ws");

    ws.onopen = () => {
      console.log("Inspector WebSocket connected");
      set({ isConnected: true, ws });
    };

    ws.onclose = () => {
      console.log("Inspector WebSocket disconnected. Retrying in 3 seconds...");
      set({ isConnected: false, ws: null });
      setTimeout(() => get().connect(), 3000); // Auto-reconnect
    };

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const { addMachine, updateMachineTransition, addService, removeService, addLog } = get();

        // Dispatch incoming messages to the correct state mutator
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
            // Handle all other events as generic logs if the machine exists
            if (get().machines[msg.machine_id]) {
              addLog(msg.machine_id, { type: msg.type, payload: msg.payload, ...msg });
            }
            break;
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", event.data, e);
      }
    };

    set({ ws });
  },

  // Action to send commands from the UI to the backend server
  sendCommand: (command: string, payload: object = {}) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ command, ...payload }));
    } else {
      console.warn("Could not send command, WebSocket is not open.", { command, payload });
    }
  },

  // --- State Mutators (used by the onmessage handler) ---

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
          lastTransition: null,
        },
      },
    })),

  updateMachineTransition: (data) =>
    set((state) => {
      const machine = state.machines[data.machine_id];
      if (!machine) return state;

      // Use the last known state as the source for the animation
      const sourceId = machine.currentStateIds.length > 0 ? machine.currentStateIds[0] : "";
      const targetId = data.to_state_ids.length > 0 ? data.to_state_ids[0] : "";

      return {
        machines: {
          ...state.machines,
          [data.machine_id]: {
            ...machine,
            currentStateIds: data.to_state_ids,
            context: data.full_context,
            lastTransition: { sourceId, targetId, event: data.event },
            logs: [...machine.logs, { type: "transition", payload: data }],
          },
        },
      };
    }),

  clearLastTransition: (machineId: string) =>
    set((state) => {
      if (!state.machines[machineId]) return state;
      return {
        machines: {
          ...state.machines,
          [machineId]: { ...state.machines[machineId], lastTransition: null },
        },
      };
    }),

  addService: (data) =>
    set((state) => {
      const machine = state.machines[data.machine_id];
      if (!machine) return state;
      return {
        machines: {
          ...state.machines,
          [data.machine_id]: {
            ...machine,
            services: { ...machine.services, [data.id]: { src: data.service, status: "running" } },
            logs: [...machine.logs, { type: "service_invoked", payload: data }],
          },
        },
      };
    }),

  removeService: (data) =>
    set((state) => {
      const machine = state.machines[data.machine_id];
      if (!machine) return state;
      const newServices = { ...machine.services };
      delete newServices[data.id];
      return {
        machines: { ...state.machines, [data.machine_id]: { ...machine, services: newServices } },
      };
    }),

  addLog: (machineId, log) =>
    set((state) => {
      const machine = state.machines[machineId];
      if (!machine) return state;
      return {
        machines: { ...state.machines, [machineId]: { ...machine, logs: [...machine.logs, log] } },
      };
    }),
}));

// --- Main React Hook ---
// This hook is used in App.tsx to ensure the WebSocket connection is initialized once.
export const useInspectorSocket = () => {
  const connect = useInspectorStore((state) => state.connect);
  useEffect(() => {
    connect();
  }, [connect]);
};
