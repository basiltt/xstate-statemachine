// src/store/slices/uiSlice.ts

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface UISliceState {
  // Loading states
  isLoading: boolean;
  loadingMessage: string | null;

  // Error handling
  error: string | null;
  errorDetails: any;

  // Notifications
  notifications: Array<{
    id: string;
    type: "success" | "error" | "warning" | "info";
    message: string;
    timestamp: number;
    autoClose?: boolean;
  }>;

  // Modal states
  modals: {
    settingsOpen: boolean;
    helpOpen: boolean;
    debugOpen: boolean;
  };

  // Panel states
  panels: {
    sidebarOpen: boolean;
    propertiesOpen: boolean;
    logsOpen: boolean;
    minimapOpen: boolean;
  };

  // Theme and preferences
  theme: "light" | "dark" | "system";

  // Debug mode
  debugMode: boolean;

  // Performance monitoring
  performanceMetrics: {
    renderTime: number;
    nodeCount: number;
    edgeCount: number;
    lastUpdate: number;
  };
}

const initialState: UISliceState = {
  isLoading: false,
  loadingMessage: null,
  error: null,
  errorDetails: null,
  notifications: [],
  modals: {
    settingsOpen: false,
    helpOpen: false,
    debugOpen: false,
  },
  panels: {
    sidebarOpen: true,
    propertiesOpen: false,
    logsOpen: false,
    minimapOpen: true,
  },
  theme: "system",
  debugMode: false,
  performanceMetrics: {
    renderTime: 0,
    nodeCount: 0,
    edgeCount: 0,
    lastUpdate: 0,
  },
};

/**
 * Redux slice for UI state management
 * Manages loading states, errors, notifications, modals, panels, and preferences
 */
const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    // Loading states
    setLoading: (state, action: PayloadAction<{ isLoading: boolean; message?: string }>) => {
      const { isLoading, message } = action.payload;
      state.isLoading = isLoading;
      state.loadingMessage = message || null;
    },

    // Error handling
    setError: (state, action: PayloadAction<{ message: string; details?: any }>) => {
      const { message, details } = action.payload;
      state.error = message;
      state.errorDetails = details || null;
    },

    clearError: (state) => {
      state.error = null;
      state.errorDetails = null;
    },

    // Notifications
    addNotification: (
      state,
      action: PayloadAction<Omit<UISliceState["notifications"][0], "id" | "timestamp">>,
    ) => {
      const notification = {
        ...action.payload,
        id: `notification-${Date.now()}-${Math.random()}`,
        timestamp: Date.now(),
      };
      state.notifications.push(notification);
    },

    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter((n) => n.id !== action.payload);
    },

    clearNotifications: (state) => {
      state.notifications = [];
    },

    // Modal management
    setModalOpen: (
      state,
      action: PayloadAction<{ modal: keyof UISliceState["modals"]; open: boolean }>,
    ) => {
      const { modal, open } = action.payload;
      state.modals[modal] = open;
    },

    closeAllModals: (state) => {
      Object.keys(state.modals).forEach((key) => {
        state.modals[key as keyof UISliceState["modals"]] = false;
      });
    },

    // Panel management
    setPanelOpen: (
      state,
      action: PayloadAction<{ panel: keyof UISliceState["panels"]; open: boolean }>,
    ) => {
      const { panel, open } = action.payload;
      state.panels[panel] = open;
    },

    togglePanel: (state, action: PayloadAction<keyof UISliceState["panels"]>) => {
      const panel = action.payload;
      state.panels[panel] = !state.panels[panel];
    },

    // Theme management
    setTheme: (state, action: PayloadAction<"light" | "dark" | "system">) => {
      state.theme = action.payload;
    },

    // Debug mode
    setDebugMode: (state, action: PayloadAction<boolean>) => {
      state.debugMode = action.payload;
    },

    toggleDebugMode: (state) => {
      state.debugMode = !state.debugMode;
    },

    // Performance metrics
    updatePerformanceMetrics: (
      state,
      action: PayloadAction<Partial<UISliceState["performanceMetrics"]>>,
    ) => {
      state.performanceMetrics = {
        ...state.performanceMetrics,
        ...action.payload,
        lastUpdate: Date.now(),
      };
    },

    // Bulk UI updates
    updateUIState: (state, action: PayloadAction<Partial<Omit<UISliceState, "notifications">>>) => {
      Object.assign(state, action.payload);
    },

    // Reset UI state
    resetUIState: () => initialState,
  },
});

export const {
  setLoading,
  setError,
  clearError,
  addNotification,
  removeNotification,
  clearNotifications,
  setModalOpen,
  closeAllModals,
  setPanelOpen,
  togglePanel,
  setTheme,
  setDebugMode,
  toggleDebugMode,
  updatePerformanceMetrics,
  updateUIState,
  resetUIState,
} = uiSlice.actions;

export default uiSlice.reducer;

// Selectors
export const selectIsLoading = (state: { ui: UISliceState }) => state.ui.isLoading;
export const selectLoadingMessage = (state: { ui: UISliceState }) => state.ui.loadingMessage;
export const selectError = (state: { ui: UISliceState }) => state.ui.error;
export const selectErrorDetails = (state: { ui: UISliceState }) => state.ui.errorDetails;
export const selectNotifications = (state: { ui: UISliceState }) => state.ui.notifications;
export const selectModals = (state: { ui: UISliceState }) => state.ui.modals;
export const selectPanels = (state: { ui: UISliceState }) => state.ui.panels;
export const selectTheme = (state: { ui: UISliceState }) => state.ui.theme;
export const selectDebugMode = (state: { ui: UISliceState }) => state.ui.debugMode;
export const selectPerformanceMetrics = (state: { ui: UISliceState }) =>
  state.ui.performanceMetrics;
export const selectModalOpen =
  (modal: keyof UISliceState["modals"]) => (state: { ui: UISliceState }) =>
    state.ui.modals[modal];
export const selectPanelOpen =
  (panel: keyof UISliceState["panels"]) => (state: { ui: UISliceState }) =>
    state.ui.panels[panel];
