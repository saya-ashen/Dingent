import { EmptyState } from "@/components/common/empty-state";
import { AlertDialogTrigger, AlertDialogContent, AlertDialogTitle, AlertDialogDescription, AlertDialogCancel, AlertDialogAction, AlertDialog } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { WorkflowSummary, LLMModelConfig } from "@/types/entity";
import { Trash2 } from "lucide-react";
import { WorkflowSettingsDialog } from "./workflows/WorkflowSettingsDialog";

export function WorkflowList({
  workflows,
  selectedWorkflow,
  models = [],
  onSelect,
  onDelete,
  onUpdateWorkflow,
  isUpdating,
}: {
  workflows: WorkflowSummary[];
  selectedWorkflow: WorkflowSummary | null;
  models?: LLMModelConfig[];
  onSelect: (workflow: WorkflowSummary) => void;
  onDelete: (workflowId: string) => void;
  onUpdateWorkflow?: (workflowId: string, updates: any) => void;
  isUpdating?: boolean;
}) {
  return (
    <div>
      <h3 className="mb-2 font-semibold">Workflows</h3>
      {workflows.length === 0 ? (
        <EmptyState
          title="No workflows"
          description="Create your first workflow to get started"
        />
      ) : (
        <div className="max-h-[300px] space-y-2 overflow-y-auto">
          {workflows.map((workflow) => (
            <div
              key={workflow.id}
              className={`hover:bg-muted cursor-pointer rounded border p-3 ${selectedWorkflow?.id === workflow.id
                ? "bg-primary/10 border-primary"
                : ""
                }`}
              onClick={() => onSelect(workflow)}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium">{workflow.name}</div>
                  {workflow.description && (
                    <div className="text-muted-foreground text-sm">
                      {workflow.description}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {onUpdateWorkflow && (
                    <div onClick={(e) => e.stopPropagation()}>
                      <WorkflowSettingsDialog
                        workflow={workflow as any}
                        models={models}
                        onSave={(updates) => onUpdateWorkflow(workflow.id, updates)}
                        isSaving={isUpdating || false}
                      />
                    </div>
                  )}
                  <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
                    <AlertDialogDescription>
                      Are you sure you want to delete "{workflow.name}"? This
                      action cannot be undone.
                    </AlertDialogDescription>
                    <div className="flex justify-end gap-2">
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => onDelete(workflow.id)}>
                        Delete
                      </AlertDialogAction>
                    </div>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
