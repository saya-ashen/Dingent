import { create } from "zustand";
import { getCookie, setCookie, removeCookie } from "@repo/lib/cookies";
import type { Workspace } from "@repo/api-client";

const WORKSPACE_ID_KEY = "active_workspace_id";

interface WorkspaceState {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  hydrated: boolean;

  // Actions
  setWorkspaces: (workspaces: Workspace[]) => void;
  setCurrentWorkspace: (workspace: Workspace) => void;
  switchWorkspaceById: (workspaceId: string) => void;
  reset: () => void;
  hydrate: () => void;
  addWorkspace: (workspace: Workspace) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  currentWorkspace: null,
  hydrated: false,

  setWorkspaces: (list) => {
    const { currentWorkspace } = get();
    let nextWorkspace: Workspace | null = null;

    if (!list || list.length === 0) {
      set({ workspaces: [], currentWorkspace: null });
      return;
    }

    const storedId = getCookie(WORKSPACE_ID_KEY);

    // 优先级 1: 内存中已选中的，优先保留 (防止 SWR/ReactQuery 重新验证数据时重置用户选择)
    if (currentWorkspace && list.find((w) => w.id === currentWorkspace.id)) {
      nextWorkspace = currentWorkspace;
    }
    // 优先级 2: Cookie 中记录的
    else if (storedId) {
      nextWorkspace = list.find((w) => w.id === storedId) || list[0] || null;
    }
    // 优先级 3: 默认第一个
    else {
      nextWorkspace = list[0] || null;
    }

    // 同步 Cookie (仅当 ID 变化时)
    if (nextWorkspace && nextWorkspace.id !== storedId) {
      setCookie(WORKSPACE_ID_KEY, nextWorkspace.id);
    }

    set({ workspaces: list, currentWorkspace: nextWorkspace });
  },

  setCurrentWorkspace: (workspace) => {
    setCookie(WORKSPACE_ID_KEY, workspace.id);
    set({ currentWorkspace: workspace });
  },

  switchWorkspaceById: (id) => {
    const list = get().workspaces;
    const target = list.find((w) => w.id === id);
    if (target) {
      get().setCurrentWorkspace(target);
    }
  },

  reset: () => {
    removeCookie(WORKSPACE_ID_KEY);
    set({ workspaces: [], currentWorkspace: null });
  },

  addWorkspace: (newWorkspace) => {
    const { workspaces } = get();
    // 乐观更新：先更新 UI，假设后端成功了 (通常是在 API 调用成功后调用此方法)
    set({
      workspaces: [...workspaces, newWorkspace],
      currentWorkspace: newWorkspace,
    });
    setCookie(WORKSPACE_ID_KEY, newWorkspace.id);
  },

  hydrate: () => {
    set({ hydrated: true });
  },
}));

// --- 导出给 API Client 使用的静态方法 ---

export const { getState: getWorkspaceState } = useWorkspaceStore;




