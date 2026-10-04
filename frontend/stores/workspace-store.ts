"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Workspace } from "@/types";

interface WorkspaceState {
  current: Workspace | null;
  list: Workspace[];
  setCurrent: (ws: Workspace | null) => void;
  setList: (list: Workspace[]) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      current: null,
      list: [],
      setCurrent: (current) => set({ current }),
      setList: (list) => set({ list }),
    }),
    { name: "cf-workspace" },
  ),
);
