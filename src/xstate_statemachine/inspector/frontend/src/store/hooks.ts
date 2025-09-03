// src/store/hooks.ts

import { useDispatch, useSelector, TypedUseSelectorHook } from "react-redux";
import type { RootState, AppDispatch } from "./index";

/**
 * Typed version of useDispatch hook for the app
 */
export const useAppDispatch = () => useDispatch<AppDispatch>();

/**
 * Typed version of useSelector hook for the app
 */
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
