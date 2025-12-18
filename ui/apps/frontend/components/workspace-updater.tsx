"use client";

import { useEffect } from "react";

import type { Workspace } from "@repo/api-client";
import { useWorkspaceStore } from "@repo/store";

interface WorkspaceUpdaterProps {
  currentWorkspace: Workspace;
  workspaces: Workspace[];
}

export function WorkspaceUpdater({ currentWorkspace, workspaces }: WorkspaceUpdaterProps) {
  const setCurrentWorkspace = useWorkspaceStore((state) => state.setCurrentWorkspace);
  const setWorkspaces = useWorkspaceStore((state) => state.setWorkspaces);

  useEffect(() => {
    setWorkspaces(workspaces);
    setCurrentWorkspace(currentWorkspace);
  }, [workspaces, currentWorkspace]);

  return null;
}
