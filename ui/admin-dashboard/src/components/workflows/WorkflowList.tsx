// src/components/workflows/WorkflowList.tsx
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { EmptyState } from "@/components/EmptyState";
import type { Workflow } from "@/lib/types";

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
            <h3 className="font-semibold mb-2">Workflows</h3>
            {workflows.length === 0 ? (
                <EmptyState title="No workflows" description="Create your first workflow to get started" />
            ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {workflows.map((workflow) => (
                        <div
                            key={workflow.id}
                            className={`p-3 border rounded cursor-pointer hover:bg-muted ${selectedWorkflow?.id === workflow.id ? "bg-primary/10 border-primary" : ""
                                }`}
                            onClick={() => onSelect(workflow)}
                        >
                            <div className="flex justify-between items-start">
                                <div>
                                    <div className="font-medium">{workflow.name}</div>
                                    {workflow.description && (
                                        <div className="text-sm text-muted-foreground">{workflow.description}</div>
                                    )}
                                </div>
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="p-1 h-auto"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <Trash2 size={14} />
                                        </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
                                        <AlertDialogDescription>
                                            Are you sure you want to delete "{workflow.name}"? This action cannot be undone.
                                        </AlertDialogDescription>
                                        <div className="flex justify-end gap-2">
                                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                                            <AlertDialogAction onClick={() => onDelete(workflow.id)}>Delete</AlertDialogAction>
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
