"use client";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Header,
  Main,
  LoadingSkeleton,
  ProfileDropdown,
  Search,
  ThemeSwitch,
  ConfigDrawer,
} from "@repo/ui/components";
import { WorkflowsSidebar } from "../../../components/workflows/WorkflowsSidebar";
import { WorkflowEditorPanel } from "../../../components/workflows/WorkflowEditorPanel";
import {
  useAssistantsConfig,
  useCreateWorkflow,
  useDeleteWorkflow,
  useSaveWorkflow,
  useWorkflowsList,
} from "@repo/store";
import { WorkflowSummary } from "@repo/api-client";

export default function WorkflowsPage() {
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [nodeAssistantIds, setNodeAssistantIds] = useState<Set<string>>(new Set());

  const workflowsQ = useWorkflowsList();
  const assistantsQ = useAssistantsConfig();

  const createWorkflow = useCreateWorkflow();
  const saveWorkflow = useSaveWorkflow();
  const deleteWorkflow = useDeleteWorkflow();

  const workflows = workflowsQ.data || [];
  const allAssistants = assistantsQ.data || [];

  const paletteAssistants = useMemo(() => {
    console.log("Filtering assistants, nodeAssistantIds:", nodeAssistantIds);
    return allAssistants.filter(a => !nodeAssistantIds.has(a.id));
  }, [allAssistants, nodeAssistantIds]);

  if (workflowsQ.isLoading || assistantsQ.isLoading)
    return <LoadingSkeleton lines={5} />;
  if (workflowsQ.error || assistantsQ.error)
    return <div className="text-red-600">Failed to load data.</div>;

  return (
    <>
      <Header>
        <Search />
        <div className="ms-auto flex items-center gap-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>
      <Main>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workflows</h1>
          <p className="text-muted-foreground">
            Design and manage task handoff workflows between assistants
          </p>
        </div>
        <div className="mt-4 flex min-h-0 w-full flex-1 gap-8 px-4 md:px-8">
          <WorkflowsSidebar
            workflows={workflows}
            selectedId={selectedWorkflowId}
            onSelect={(wf: WorkflowSummary | null) =>
              setSelectedWorkflowId(wf ? wf.id : null)
            }
            onCreateWorkflow={(input) =>
              createWorkflow.mutate(input, {
                onSuccess: (wf) => {
                  toast.success("Workflow created");
                  setSelectedWorkflowId(wf.id);
                },
                onError: e => toast.error(`Failed to create workflow: ${e?.message || e}`),
              })
            }
            onDeleteWorkflow={(id) =>
              deleteWorkflow.mutate(id, {
                onSuccess: () => {
                  toast.success("Workflow deleted");
                  setSelectedWorkflowId((cur) => (cur === id ? null : cur));
                },
                onError: e => toast.error(`Failed to delete workflow: ${e?.message || e}`),
              })
            }
            paletteAssistants={paletteAssistants}
          />

          <main className="min-h-0 flex-1">
            <WorkflowEditorPanel
              workflowId={selectedWorkflowId}
              isSaving={saveWorkflow.isPending}
              onSave={(wf) =>
                saveWorkflow.mutate(wf, {
                  onSuccess: () => toast.success("Workflow saved"),
                  onError: e => toast.error(`Failed to save workflow: ${e?.message || e}`),
                })
              }
              onNodeAssistantIdsChange={setNodeAssistantIds}
            />
          </main>
        </div>
      </Main>
    </>
  );
}
