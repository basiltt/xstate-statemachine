// src/services/websocketService.ts

import { store } from "../store";
import {
  setConnected,
  setConnectionError,
  setLastConnectionAttempt,
  addMachine,
  updateMachineState,
  updateMachineContext,
  addLog,
  updateServices,
  setLastTransition,
} from "../store/slices/machineSlice";
import { addNotification } from "../store/slices/uiSlice";
import type { LogEntry } from "../store/api/inspectorApi";

/**
 * WebSocket service for managing inspector connections
 * Replaces the Zustand-based useInspectorSocket hook
 */
class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private url = "ws://127.0.0.1:8008/ws";

  /**
   * Initialize WebSocket connection
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log("[WebSocket] Already connected");
      return;
    }

    try {
      console.log("[WebSocket] Attempting to connect to:", this.url);
      store.dispatch(setLastConnectionAttempt(Date.now()));

      this.ws = new WebSocket(this.url);
      this.setupEventHandlers();
    } catch (error) {
      console.error("[WebSocket] Connection failed:", error);
      this.handleConnectionError("Failed to create WebSocket connection");
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log("[WebSocket] Connected successfully");
      store.dispatch(setConnected(true));
      store.dispatch(
        addNotification({
          type: "success",
          message: "Inspector connected successfully",
          autoClose: true,
        }),
      );
      this.reconnectAttempts = 0;
    };

    this.ws.onclose = (event) => {
      console.log("[WebSocket] Disconnected:", event.code, event.reason);
      store.dispatch(setConnected(false));

      if (!event.wasClean) {
        this.handleReconnection();
      }
    };

    this.ws.onerror = (error) => {
      console.error("[WebSocket] Error:", error);
      this.handleConnectionError("WebSocket connection error");
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(event);
    };
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const msg = JSON.parse(event.data);
      console.log("[WebSocket] Received message:", msg);

      switch (msg.type) {
        case "machine_registered":
          this.handleMachineRegistered(msg.payload);
          break;
        case "transition":
          this.handleTransition(msg.payload);
          break;
        case "service_invoked":
          this.handleServiceInvoked(msg.payload);
          break;
        case "service_stopped":
          this.handleServiceStopped(msg.payload);
          break;
        default:
          this.handleGenericEvent(msg);
          break;
      }
    } catch (error) {
      console.error("[WebSocket] Failed to parse message:", error, "Raw data:", event.data);
      store.dispatch(
        addNotification({
          type: "error",
          message: "Failed to parse WebSocket message",
          autoClose: true,
        }),
      );
    }
  }

  /**
   * Handle machine registration
   */
  private handleMachineRegistered(data: any): void {
    console.log("[WebSocket] Adding machine:", data);
    const timestamp = typeof data.timestamp === "number" ? data.timestamp : Date.now();

    const machineState = {
      id: data.machine_id,
      definition: data.definition,
      currentStateIds: data.initial_state_ids || [],
      context: data.initial_context || {},
      logs: [
        { type: "machine_registered", payload: data, timestamp: new Date().toISOString() },
      ] as LogEntry[],
      services: {},
      lastTransition: null,
      registeredAt: timestamp,
      updatedAt: timestamp,
    };

    store.dispatch(addMachine(machineState));
    store.dispatch(
      addNotification({
        type: "info",
        message: `Machine "${data.machine_id}" registered`,
        autoClose: true,
      }),
    );
  }

  /**
   * Handle state transitions
   */
  private handleTransition(data: any): void {
    console.log("[WebSocket] Machine transition:", data);
    const { machine_id, to_state_ids, full_context, event } = data;

    // Update machine state
    store.dispatch(
      updateMachineState({
        machineId: machine_id,
        stateIds: to_state_ids || [],
      }),
    );

    // Update context
    if (full_context !== undefined) {
      store.dispatch(
        updateMachineContext({
          machineId: machine_id,
          context: full_context,
        }),
      );
    }

    // Set last transition for animation
    const state = store.getState();
    const machine = state.machine.machines[machine_id];
    if (machine) {
      const sourceId = machine.currentStateIds.length > 0 ? machine.currentStateIds[0] : "";
      const targetId = to_state_ids && to_state_ids.length > 0 ? to_state_ids[0] : "";

      store.dispatch(
        setLastTransition({
          machineId: machine_id,
          transition: { sourceId, targetId, event: event || "unknown" },
        }),
      );
    }

    // Add log entry
    store.dispatch(
      addLog({
        machineId: machine_id,
        log: {
          type: "transition",
          payload: data,
          timestamp: new Date().toISOString(),
          machine_id,
        },
      }),
    );
  }

  /**
   * Handle service invocation
   */
  private handleServiceInvoked(data: any): void {
    console.log("[WebSocket] Service invoked:", data);
    const { machine_id, id, service } = data;

    const state = store.getState();
    const machine = state.machine.machines[machine_id];
    if (machine) {
      const updatedServices = {
        ...machine.services,
        [id]: { src: service, status: "running" },
      };

      store.dispatch(
        updateServices({
          machineId: machine_id,
          services: updatedServices,
        }),
      );

      store.dispatch(
        addLog({
          machineId: machine_id,
          log: {
            type: "service_invoked",
            payload: data,
            timestamp: new Date().toISOString(),
            machine_id,
          },
        }),
      );
    }
  }

  /**
   * Handle service stopping
   */
  private handleServiceStopped(data: any): void {
    console.log("[WebSocket] Service stopped:", data);
    const { machine_id, id } = data;

    const state = store.getState();
    const machine = state.machine.machines[machine_id];
    if (machine) {
      const updatedServices = { ...machine.services };
      delete updatedServices[id];

      store.dispatch(
        updateServices({
          machineId: machine_id,
          services: updatedServices,
        }),
      );

      store.dispatch(
        addLog({
          machineId: machine_id,
          log: {
            type: "service_stopped",
            payload: data,
            timestamp: new Date().toISOString(),
            machine_id,
          },
        }),
      );
    }
  }

  /**
   * Handle generic events as logs
   */
  private handleGenericEvent(msg: any): void {
    console.log("[WebSocket] Generic event:", msg.type, msg);

    if (msg.machine_id) {
      const state = store.getState();
      if (state.machine.machines[msg.machine_id]) {
        store.dispatch(
          addLog({
            machineId: msg.machine_id,
            log: {
              type: msg.type,
              payload: msg.payload,
              timestamp: new Date().toISOString(),
              machine_id: msg.machine_id,
            },
          }),
        );
      }
    }
  }

  /**
   * Handle connection errors
   */
  private handleConnectionError(message: string): void {
    store.dispatch(setConnectionError(message));
    store.dispatch(
      addNotification({
        type: "error",
        message: `Connection error: ${message}`,
        autoClose: false,
      }),
    );
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("[WebSocket] Max reconnection attempts reached");
      store.dispatch(setConnectionError("Max reconnection attempts reached"));
      return;
    }

    this.reconnectAttempts++;
    console.log(
      `[WebSocket] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
    );

    store.dispatch(
      addNotification({
        type: "warning",
        message: `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
        autoClose: true,
      }),
    );

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
  }

  /**
   * Send command to the server
   */
  sendCommand(command: string, payload: object = {}): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ command, ...payload });
      console.log("[WebSocket] Sending command:", { command, payload });
      this.ws.send(message);
    } else {
      console.warn("[WebSocket] Cannot send command, connection not open:", { command, payload });
      store.dispatch(
        addNotification({
          type: "warning",
          message: "Cannot send command: WebSocket not connected",
          autoClose: true,
        }),
      );
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, "Manual disconnect");
      this.ws = null;
    }

    store.dispatch(setConnected(false));
    console.log("[WebSocket] Disconnected manually");
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export hook for React components
export const useWebSocketService = () => {
  return {
    connect: () => websocketService.connect(),
    disconnect: () => websocketService.disconnect(),
    sendCommand: (command: string, payload?: object) =>
      websocketService.sendCommand(command, payload),
    isConnected: () => websocketService.isConnected(),
  };
};
