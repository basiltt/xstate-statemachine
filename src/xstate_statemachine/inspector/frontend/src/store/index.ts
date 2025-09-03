// src/store/index.ts

import { configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { inspectorApi } from "./api/inspectorApi";
import machineReducer from "./slices/machineSlice";
import diagramReducer from "./slices/diagramSlice";
import uiReducer from "./slices/uiSlice";

/**
 * Configure the Redux store with RTK Query
 * Includes middleware for caching, invalidation, polling, and other useful features
 */
export const store = configureStore({
  reducer: {
    // RTK Query API slice
    [inspectorApi.reducerPath]: inspectorApi.reducer,

    // Application slices
    machine: machineReducer,
    diagram: diagramReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ["persist/PERSIST", "persist/REHYDRATE"],
        // Ignore these field paths in all actions
        ignoredActionsPaths: ["meta.arg", "payload.timestamp"],
        // Ignore these paths in the state
        ignoredPaths: ["items.dates"],
      },
    })
      .concat(inspectorApi.middleware)
      // Add listener middleware for additional behavior
      .concat(/* add other middleware here */),
});

// Enable listener behavior for the store
setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
