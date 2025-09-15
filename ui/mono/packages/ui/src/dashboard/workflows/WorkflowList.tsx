import { Trash2 } from "lucide-react";
import type { Workflow } from "@repo/api-client";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "../../components/ui/alert-dialog";
import { Button } from "../../components/ui/button";
import { EmptyState } from "../../components/empty-state";

export function WorkflowList({
  workflows,
  selectedWorkflow,
  onSelect,
  onDelete,
}: {
  workflows: Workflow[];
  selectedWorkflow: Workflow | null;
  onSelect: (workflow: Workflow) => void;
  onDelete: (workflowId: string) => void;
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
              className={`hover:bg-muted cursor-pointer rounded border p-3 ${
                selectedWorkflow?.id === workflow.id
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
