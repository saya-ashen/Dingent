"use client";
import { Assistant } from "@/types/entity";
import { createContext, useContext, useState, ReactNode } from "react";

interface WorkflowContextType {
  draggedAssistant: Assistant | null;
  usedAssistantIds: Set<string>;
  setDraggedAssistant: (a: Assistant | null) => void;
  setUsedAssistantIds: (ids: Set<string>) => void;
}


const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export function WorkflowProvider({ children }: { children: ReactNode }) {
  const [draggedAssistant, setDraggedAssistant] = useState<Assistant | null>(null);
  const [usedAssistantIds, setUsedAssistantIds] = useState<Set<string>>(new Set());

  return (
    <WorkflowContext.Provider value={{
      draggedAssistant,
      setDraggedAssistant,
      usedAssistantIds,
      setUsedAssistantIds
    }}>
      {children}
    </WorkflowContext.Provider>
  );
}

export const useWorkflowContext = () => {
  const context = useContext(WorkflowContext);
  if (!context) throw new Error("useWorkflowContext must be used within WorkflowProvider");
  return context;
};
