"use client";
import { memo } from "react";
import {
  NewWorkflowDialog,
  WorkflowList,
  AssistantsPalette,
} from "@repo/ui/components";
import { Assistant, WorkflowSummary } from "@repo/api-client";


interface SidebarProps {
  workflows: WorkflowSummary[];
  selectedId: string | null;
  onSelect: (wf: WorkflowSummary | null) => void;
  onCreateWorkflow: (input: { name: string; description?: string }) => void;
  onDeleteWorkflow: (id: string) => void;
  paletteAssistants: Assistant[];
}


function WorkflowsSidebarImpl({
  workflows,
  selectedId,
  onSelect,
  onCreateWorkflow,
  onDeleteWorkflow,
  paletteAssistants,
}: SidebarProps) {
  const selected = workflows.find((w) => w.id === selectedId) || null;
  return (
    <aside className="flex w-full max-w-3xs flex-shrink-0 flex-col gap-6">
      <NewWorkflowDialog onCreateWorkflow={onCreateWorkflow} />
      <WorkflowList
        workflows={workflows}
        selectedWorkflow={selected}
        onSelect={onSelect}
        onDelete={onDeleteWorkflow}
      />
      <AssistantsPalette assistants={paletteAssistants} />
    </aside>
  );
}


export const WorkflowsSidebar = memo(WorkflowsSidebarImpl);
