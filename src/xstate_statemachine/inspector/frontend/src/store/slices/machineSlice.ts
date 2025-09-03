// src/store/slices/machineSlice.ts

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { LogEntry, MachineState } from "../api/inspectorApi";

// Re-export types for external use
export type { LogEntry, MachineState };

interface MachineSliceState {
  isConnected: boolean;
  machines: Record<string, MachineState>;
  selectedMachineId: string | null;
  connectionError: string | null;
  lastConnectionAttempt: number | null;
}

const initialState: MachineSliceState = {
  isConnected: false,
  machines: {},
  selectedMachineId: null,
  connectionError: null,
  lastConnectionAttempt: null,
};

/**
 * Redux slice for machine state management
 * Replaces the Zustand store from useInspectorSocket
 */
const machineSlice = createSlice({
  name: "machine",
  initialState,
  reducers: {
    // Connection management
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
      if (action.payload) {
        state.connectionError = null;
      }
    },

    setConnectionError: (state, action: PayloadAction<string>) => {
      state.connectionError = action.payload;
      state.isConnected = false;
    },

    setLastConnectionAttempt: (state, action: PayloadAction<number>) => {
      state.lastConnectionAttempt = action.payload;
    },

    // Machine management
    addMachine: (state, action: PayloadAction<MachineState>) => {
      const machine = action.payload;
      state.machines[machine.id] = machine;
    },

    updateMachine: (state, action: PayloadAction<Partial<MachineState> & { id: string }>) => {
      const { id, ...updates } = action.payload;
      if (state.machines[id]) {
        state.machines[id] = { ...state.machines[id], ...updates, updatedAt: Date.now() };
      }
    },

    removeMachine: (state, action: PayloadAction<string>) => {
      delete state.machines[action.payload];
      if (state.selectedMachineId === action.payload) {
        state.selectedMachineId = null;
      }
    },

    setSelectedMachine: (state, action: PayloadAction<string | null>) => {
      state.selectedMachineId = action.payload;
    },

    // State updates
    updateMachineState: (
      state,
      action: PayloadAction<{ machineId: string; stateIds: string[] }>,
    ) => {
      const { machineId, stateIds } = action.payload;
      if (state.machines[machineId]) {
        state.machines[machineId].currentStateIds = stateIds;
        state.machines[machineId].updatedAt = Date.now();
      }
    },

    updateMachineContext: (state, action: PayloadAction<{ machineId: string; context: any }>) => {
      const { machineId, context } = action.payload;
      if (state.machines[machineId]) {
        state.machines[machineId].context = context;
        state.machines[machineId].updatedAt = Date.now();
      }
    },

    // Logs management
    addLog: (state, action: PayloadAction<{ machineId: string; log: LogEntry }>) => {
      const { machineId, log } = action.payload;
      if (state.machines[machineId]) {
        state.machines[machineId].logs.push(log);
        state.machines[machineId].updatedAt = Date.now();
      }
    },

    clearLogs: (state, action: PayloadAction<string>) => {
      const machineId = action.payload;
      if (state.machines[machineId]) {
        state.machines[machineId].logs = [];
        state.machines[machineId].updatedAt = Date.now();
      }
    },

    // Services management
    updateServices: (
      state,
      action: PayloadAction<{
        machineId: string;
        services: Record<string, { src: string; status: string }>;
      }>,
    ) => {
      const { machineId, services } = action.payload;
      if (state.machines[machineId]) {
        state.machines[machineId].services = services;
        state.machines[machineId].updatedAt = Date.now();
      }
    },

    // Transition tracking
    setLastTransition: (
      state,
      action: PayloadAction<{
        machineId: string;
        transition: { sourceId: string; targetId: string; event: string } | null;
      }>,
    ) => {
      const { machineId, transition } = action.payload;
      if (state.machines[machineId]) {
        state.machines[machineId].lastTransition = transition;
        state.machines[machineId].updatedAt = Date.now();
      }
    },

    // Reset all state
    resetMachineState: () => initialState,
  },
});

export const {
  setConnected,
  setConnectionError,
  setLastConnectionAttempt,
  addMachine,
  updateMachine,
  removeMachine,
  setSelectedMachine,
  updateMachineState,
  updateMachineContext,
  addLog,
  clearLogs,
  updateServices,
  setLastTransition,
  resetMachineState,
} = machineSlice.actions;

export default machineSlice.reducer;

// Selectors
export const selectIsConnected = (state: { machine: MachineSliceState }) =>
  state.machine.isConnected;
export const selectMachines = (state: { machine: MachineSliceState }) => state.machine.machines;
export const selectSelectedMachineId = (state: { machine: MachineSliceState }) =>
  state.machine.selectedMachineId;
export const selectSelectedMachine = (state: { machine: MachineSliceState }) => {
  const { machines, selectedMachineId } = state.machine;
  return selectedMachineId ? machines[selectedMachineId] : null;
};
export const selectConnectionError = (state: { machine: MachineSliceState }) =>
  state.machine.connectionError;
export const selectMachineById = (machineId: string) => (state: { machine: MachineSliceState }) =>
  state.machine.machines[machineId];
