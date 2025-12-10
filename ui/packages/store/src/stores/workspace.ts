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

  /**
   * 设置工作空间列表。
   * 智能逻辑：当列表更新时，如果当前没有选中的 workspace，或者选中的 id 不在列表中，
   * 自动回退到列表的第一个（默认空间）。
   */
  setWorkspaces: (list) => {
    const { currentWorkspace } = get();
    let nextWorkspace: Workspace | null = null; // 初始化为 null

    // 安全检查：如果列表为空，直接清空
    if (!list || list.length === 0) {
      set({ workspaces: [], currentWorkspace: null });
      return;
    }

    const storedId = getCookie(WORKSPACE_ID_KEY);

    // 优先级 1: 如果当前 store 里已经有一个 workspace，且它依然在新的 list 里，保持不变
    // 这防止了比如 API 轮询刷新列表时，把用户正在操作的 active 状态重置了
    if (currentWorkspace && list.find(w => w.id === currentWorkspace.id)) {
      nextWorkspace = currentWorkspace;
    }
    // 优先级 2: 使用 Cookie 恢复
    else if (storedId) {
      const found = list.find((w) => w.id === storedId);
      if (found) {
        nextWorkspace = found;
      } else {
        nextWorkspace = list[0] || null;
      }
    }
    // 优先级 3: 默认第一个
    else {
      nextWorkspace = list[0] || null;
    }

    // 同步 Cookie
    if (nextWorkspace) {
      // 只有当 ID 真的变了才写 Cookie，减少 IO
      if (nextWorkspace.id !== storedId) {
        setCookie(WORKSPACE_ID_KEY, nextWorkspace.id);
      }
    }

    set({ workspaces: list, currentWorkspace: nextWorkspace });
  },

  /**
   * 手动切换当前工作空间
   */
  setCurrentWorkspace: (workspace) => {
    setCookie(WORKSPACE_ID_KEY, workspace.id);
    set({ currentWorkspace: workspace });
  },

  /**
   * 便捷方法：通过 ID 切换
   */
  switchWorkspaceById: (id) => {
    const list = get().workspaces;
    const target = list.find((w) => w.id === id);
    if (target) {
      get().setCurrentWorkspace(target);
      // 切换空间通常建议刷新页面或重置路由，以防数据混淆
      // window.location.reload(); // 可选：暴力刷新
    }
  },

  reset: () => {
    removeCookie(WORKSPACE_ID_KEY);
    set({ workspaces: [], currentWorkspace: null });
  },

  addWorkspace: (newWorkspace) => {
    const { workspaces } = get();
    // 1. 更新列表
    const newList = [...workspaces, newWorkspace];

    // 2. 更新状态 (并自动切换到新创建的空间，这是常见体验)
    set({
      workspaces: newList,
      currentWorkspace: newWorkspace
    });

    // 3. 别忘了同步 Cookie
    setCookie(WORKSPACE_ID_KEY, newWorkspace.id);
  },

  hydrate: () => {
    // 对于 Workspace 来说，hydrate 主要是在 API 请求回来之前，
    // 我们可以先拿到 ID，但具体的 Workspace 对象通常依赖后端返回的 list。
    // 所以这里的 hydrate 主要是标记状态。
    set({ hydrated: true });
  },
}));

// 导出非 hook 方法供 API Client 使用
export const { getState: getWorkspaceState } = useWorkspaceStore;
