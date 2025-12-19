"use client";

import { useState, useEffect } from "react";
import { Assistant } from "@/types/entity";

export function useAssistantEditor(serverData: Assistant[] | undefined) {
  const [editable, setEditable] = useState<Assistant[]>([]);
  const [dirtyIds, setDirtyIds] = useState<Set<string>>(new Set());

  // Sync with server data when it loads
  useEffect(() => {
    if (serverData) {
      setEditable(JSON.parse(JSON.stringify(serverData)));
      setDirtyIds(new Set()); // Reset dirty state on fresh load
    }
  }, [serverData]);

  const updateAssistant = (index: number, updated: Assistant) => {
    const nextState = [...editable];
    nextState[index] = updated;
    setEditable(nextState);
    setDirtyIds((prev) => new Set(prev).add(updated.id));
  };

  const getDirtyAssistants = () => {
    return editable.filter((a) => dirtyIds.has(a.id));
  };

  return {
    editable,
    dirtyIds,
    hasChanges: dirtyIds.size > 0,
    updateAssistant,
    getDirtyAssistants,
  };
}
