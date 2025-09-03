// src/store/api/inspectorApi.ts

import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import axios from "axios";

// Types for the inspector API
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
  lastTransition: { sourceId: string; targetId: string; event: string } | null;
  registeredAt: number;
  updatedAt: number;
}

export interface InspectorState {
  isConnected: boolean;
  machines: Record<string, MachineState>;
  selectedMachineId: string | null;
}

/**
 * RTK Query API slice for inspector operations
 * Note: Since the current implementation uses WebSocket, we'll create endpoints
 * for potential HTTP operations and maintain WebSocket logic separately
 */
export const inspectorApi = createApi({
  reducerPath: "inspectorApi",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api/",
    prepareHeaders: (headers) => {
      headers.set("Content-Type", "application/json");
      return headers;
    },
  }),
  tagTypes: ["Machine", "Connection"],
  endpoints: (builder) => ({
    // Get machine state (if HTTP endpoint exists)
    getMachine: builder.query<MachineState, string>({
      query: (machineId) => `machines/${machineId}`,
      providesTags: (_result, _error, machineId) => [{ type: "Machine", id: machineId }],
    }),

    // Get all machines (if HTTP endpoint exists)
    getMachines: builder.query<Record<string, MachineState>, void>({
      query: () => "machines",
      providesTags: ["Machine"],
    }),

    // Send event to machine (if HTTP endpoint exists)
    sendEvent: builder.mutation<void, { machineId: string; event: any }>({
      query: ({ machineId, event }) => ({
        url: `machines/${machineId}/events`,
        method: "POST",
        body: event,
      }),
      invalidatesTags: (_result, _error, { machineId }) => [{ type: "Machine", id: machineId }],
    }),

    // Check connection status
    getConnectionStatus: builder.query<{ connected: boolean }, void>({
      query: () => "status",
      providesTags: ["Connection"],
    }),
  }),
});

// Export hooks for components
export const {
  useGetMachineQuery,
  useGetMachinesQuery,
  useSendEventMutation,
  useGetConnectionStatusQuery,
} = inspectorApi;

/**
 * Axios instance for additional HTTP requests
 */
export const axiosInstance = axios.create({
  baseURL: "/api/",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    console.log("API Request:", config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error("API Request Error:", error);
    return Promise.reject(error);
  },
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => {
    console.log("API Response:", response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error("API Response Error:", error.response?.status, error.config?.url, error.message);
    return Promise.reject(error);
  },
);
