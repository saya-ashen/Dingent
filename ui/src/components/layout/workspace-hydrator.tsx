"use client";

import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@/store";
import { Workspace } from "@/types/entity";

interface WorkspaceHydratorProps {
  workspaces: Workspace[];
  currentWorkspace?: Workspace | null;
}

export function WorkspaceHydrator({
  workspaces,
  currentWorkspace = null
}: WorkspaceHydratorProps) {
  const initialized = useRef(false);

  const setWorkspaces = useWorkspaceStore((state) => state.setWorkspaces);
  const setCurrentWorkspace = useWorkspaceStore((state) => state.setCurrentWorkspace);

  useEffect(() => {
    setWorkspaces(workspaces);

    if (currentWorkspace) {
      setCurrentWorkspace(currentWorkspace);
    }
  }, [workspaces, currentWorkspace, setWorkspaces, setCurrentWorkspace]);

  return null;
}
