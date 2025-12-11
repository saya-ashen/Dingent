"use client";

import { useEffect, useRef } from "react"; // 引入 useRef 防止 React Strict Mode 下的双重请求
import { useWorkspaceStore, useAuthStore } from "@repo/store";
import { Workspace } from "@repo/api-client";

export function WorkspaceInitializer({ workspaces }: { workspaces: Workspace[] }) {
  const { setWorkspaces, hydrated, hydrate } = useWorkspaceStore();
  const { accessToken } = useAuthStore();

  const isFetching = useRef(false);

  useEffect(() => {
    const initWorkspaces = async () => {
      if (!accessToken || hydrated || isFetching.current) return;

      isFetching.current = true; // 标记正在请求

      try {

        setWorkspaces(workspaces);

        hydrate();
      } catch (error) {
        console.error("Failed to fetch workspaces:", error);
        // 这里可以考虑 toast 提示，或者不处理（静默失败）
      } finally {
        isFetching.current = false;
      }
    };

    initWorkspaces();
  }, [accessToken, hydrated, hydrate, setWorkspaces]); // 依赖项

  return null;
}
