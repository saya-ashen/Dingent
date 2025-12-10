"use client";

import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@repo/store";
import type { Workspace } from "@repo/api-client";

export function WorkspaceUpdater({ workspace }: { workspace: Workspace }) {
  const setCurrentWorkspace = useWorkspaceStore((s) => s.setCurrentWorkspace);

  const lastId = useRef(workspace.id);

  useEffect(() => {
    setCurrentWorkspace(workspace);
  }, [workspace, setCurrentWorkspace]);

  return null;
}
