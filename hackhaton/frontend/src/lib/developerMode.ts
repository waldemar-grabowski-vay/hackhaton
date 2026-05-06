/**
 * Developer mode store (T021, FR-020 / FR-021).
 *
 * Backed by localStorage so the toggle persists across reloads. Default OFF
 * (Operator mode) on first load. Toggling MUST NOT trigger a re-fetch — this
 * store does not touch the network or the run cache.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface DeveloperModeState {
  enabled: boolean;
  toggle: () => void;
  set: (value: boolean) => void;
}

export const useDeveloperMode = create<DeveloperModeState>()(
  persist(
    (set, get) => ({
      enabled: false,
      toggle: () => set({ enabled: !get().enabled }),
      set: (value) => set({ enabled: value }),
    }),
    {
      name: "vayobd.developerMode.v1",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
