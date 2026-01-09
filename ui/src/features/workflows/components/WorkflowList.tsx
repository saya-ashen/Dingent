import { EmptyState } from "@/components/common/empty-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { WorkflowSettingsDialog } from "./workflows/WorkflowSettingsDialog";
import { WorkflowSummary, LLMModelConfig } from "@/types/entity";
import { Trash2 } from "lucide-react";

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

                {/* 修复点 2: 这里的 flex gap 布局之前被 block div 破坏了。
                   确保子元素也是 flex 行为，或者不破坏流。
                */}
                <div className="flex items-center gap-1">
                  {onUpdateWorkflow && (
                    <div
                      onClick={(e) => e.stopPropagation()}
                      className="flex" // <--- 修复布局问题
                    >
                      <WorkflowSettingsDialog
                        workflow={workflow as any}
                        models={models}
                        // 修复点 1: TypeScript 安全调用
                        onSave={(updates) =>
                          onUpdateWorkflow?.(workflow.id, updates)
                        }
                        isSaving={isUpdating || false}
                      />
                    </div>
                  )}

                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-1 text-muted-foreground hover:text-destructive" // 建议添加 hover 颜色
                        onClick={(e) => e.stopPropagation()} // 阻止点击行选中的冒泡
                      >
                        <Trash2 size={14} />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent
                      // 阻止 Dialog 内部点击冒泡（通常不需要，因为是 Portal，但加上保险）
                      onClick={(e) => e.stopPropagation()}
                    >
                      <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete "{workflow.name}"? This
                        action cannot be undone.
                      </AlertDialogDescription>
                      <div className="flex justify-end gap-2">
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          className="bg-destructive hover:bg-destructive/90" // 建议使用 destructive 样式
                          onClick={(e) => {
                            // 阻止事件冒泡 (虽然通常不需要，但在某些情况下防止触发父级点击)
                            e.stopPropagation();
                            onDelete(workflow.id);
                          }}
                        >
                          Delete
                        </AlertDialogAction>
                      </div>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
