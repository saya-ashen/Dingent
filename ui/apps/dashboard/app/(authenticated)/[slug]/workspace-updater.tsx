"use client";

import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@repo/store";
import type { Workspace } from "@repo/api-client";

export function WorkspaceUpdater({ currentWorkspace, workspaces }: { currentWorkspace: Workspace, workspaces: Workspace[] }) {
  const setCurrentWorkspace = useWorkspaceStore((s) => s.setCurrentWorkspace);
  const setWorkspaces = useWorkspaceStore((state) => state.setWorkspaces);
  useEffect(() => {
    setWorkspaces(workspaces);
  }, [workspaces, setWorkspaces]);


  const lastId = useRef(currentWorkspace.id);

  useEffect(() => {
    setCurrentWorkspace(currentWorkspace);
  }, [currentWorkspace, setCurrentWorkspace]);

  return null;
}
