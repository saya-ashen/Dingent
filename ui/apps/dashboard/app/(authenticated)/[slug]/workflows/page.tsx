"use client";
import { useState } from "react";
import { Header, Main, LoadingSkeleton } from "@repo/ui/components";
import { useAssistantsConfig, useWorkflowsList, useSaveWorkflow } from "@repo/store";
import { useParams } from "next/navigation";
import { getClientApi } from "@/lib/api/client";
import { WorkflowProvider } from "@/components/workflows/WorkflowContext";
import { WorkflowSidebar } from "@/components/workflows/WorkflowSidebar";
import { WorkflowCanvas } from "@/components/workflows/WorkflowCanvas";

export default function WorkflowsPage() {
  const params = useParams();
  const slug = params.slug as string;

  // API Setup
  const api = getClientApi().forWorkspace(slug);
  const workflowsQ = useWorkflowsList(api.workflows);
  const assistantsQ = useAssistantsConfig(api.assistants);
  const saveWorkflowMutation = useSaveWorkflow(api.workflows);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (workflowsQ.isLoading || assistantsQ.isLoading) return <LoadingSkeleton />;


  return (
    <WorkflowProvider>
      <div className="flex flex-col h-screen overflow-hidden">
        <Header>
          <span className="font-bold ml-4">Dingent Workflow Builder</span>
        </Header>

        <div className="flex flex-1 overflow-hidden">
          {/* 左侧 */}
          <WorkflowSidebar
            workflows={workflowsQ.data || []}
            assistants={assistantsQ.data || []}
            selectedWorkflowId={selectedId}
            onSelectWorkflow={setSelectedId}
          // 传入 create/delete handlers
          />

          {/* 右侧画布 */}
          <main className="flex-1 bg-background relative">
            <WorkflowCanvas
              workflowId={selectedId}
              isSaving={saveWorkflowMutation.isPending}
              onSave={(nodes, edges) => {
                if (!selectedId) return;
                const currentWorkflow = workflowsQ.data?.find(w => w.id === selectedId);
                if (!currentWorkflow) return;
                saveWorkflowMutation.mutate({ ...currentWorkflow, nodes, edges });
              }}
            />
          </main>
        </div>
      </div>
    </WorkflowProvider>
  );
}
