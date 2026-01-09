"use client";
import { useState } from "react";
import {
  useAssistantsConfig,
  useWorkflowsList,
  useSaveWorkflow,
  useCreateWorkflow,
  useDeleteWorkflow,
} from "@/features/workflows/hooks";
import { useParams } from "next/navigation";
import { getClientApi } from "@/lib/api/client";
import { WorkflowProvider } from "@/features/workflows/providers";
import { WorkflowSidebar } from "@/features/workflows/components";
import { WorkflowCanvas } from "@/features/workflows/components";
import { toast } from "sonner";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageContainer } from "@/components/common/page-container";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useMemo, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Edge, Node } from "@xyflow/react";
import { Workflow, WorkflowEdge, WorkflowNode } from "@/types/entity";

export default function WorkflowsPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const slug = params.slug as string;
  const queryClient = useQueryClient();

  // 1. URL Sync: 从 URL 获取选中 ID
  const selectedId = searchParams.get("workflowId");

  // 2. Performance: Memoize API instance
  const api = useMemo(() => getClientApi().forWorkspace(slug), [slug]);

  const workflowsQ = useWorkflowsList(api.workflows, slug);
  const assistantsQ = useAssistantsConfig(api.assistants, slug);
  const saveWorkflowMutation = useSaveWorkflow(api.workflows, slug);
  const createWorkflow = useCreateWorkflow(api.workflows, slug);
  const deleteWorkflow = useDeleteWorkflow(api.workflows, slug);

  // Helper: 处理 ID 变更，同步到 URL
  const handleSelectWorkflow = useCallback(
    (id: string | null) => {
      const newParams = new URLSearchParams(searchParams.toString());
      if (id) {
        newParams.set("workflowId", id);
      } else {
        newParams.delete("workflowId");
      }
      router.replace(`?${newParams.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  // Logic: 保存逻辑抽离
  const handleSave = useCallback(
    (nodes: WorkflowNode[], edges: WorkflowEdge[]) => {
      if (!selectedId || !workflowsQ.data) return;

      const currentWorkflow = workflowsQ.data.find((w) => w.id === selectedId);
      if (!currentWorkflow) return;

      saveWorkflowMutation.mutate(
        {
          id: currentWorkflow.id, // 显式指定 ID
          name: currentWorkflow.name, // 如果后端需要 name
          nodes,
          edges,
          // 避免 ...currentWorkflow 混入 create_at 等不必要的字段
        },
        {
          onSuccess: () => {
            // 可选：静默保存或显示 "Saved"
            // toast.success("Workflow saved");
          },
          onError: (e) => toast.error("Failed to save"),
        },
      );
    },
    [selectedId, workflowsQ.data, saveWorkflowMutation],
  );

  // Logic: 自动选中第一个 (可选体验优化)
  useEffect(() => {
    if (workflowsQ.isSuccess && workflowsQ.data.length > 0 && !selectedId) {
      // 如果需要进入页面默认选中第一个，可以在这里处理
      // handleSelectWorkflow(workflowsQ.data[0].id);
    }
  }, [workflowsQ.isSuccess, workflowsQ.data, selectedId, handleSelectWorkflow]);

  // 3. UX: 更好的 Loading 策略 (不阻塞整个页面，Sidebar 可以先出来)
  // 如果 workflows 加载慢，确实需要 skeleton。但 assistants 加载慢是否应该阻塞 UI？
  // 这里暂时保持原样，但建议由 Sidebar 内部处理 assistants 的 loading 状态。
  if (workflowsQ.isLoading) return <LoadingSkeleton />;

  return (
    <PageContainer
      title="Workflow Editor"
      description="Create and manage your workflows."
      // 4. CSS: 确保容器占满剩余高度，而不是硬编码 h-screen
      className="flex flex-col h-[calc(100vh-64px)]" // 假设 Header 是 64px
    >
      <WorkflowProvider>
        {/* 移除 h-screen，改用 h-full 适应 PageContainer 给的高度 */}
        <div className="flex flex-col h-full overflow-hidden border rounded-lg bg-background">
          <div className="flex flex-1 overflow-hidden">
            <WorkflowSidebar
              workflows={workflowsQ.data || []}
              assistants={assistantsQ.data || []} // 建议 Sidebar 内部处理 assistants 为空的情况
              models={modelsQ.data || []}
              selectedWorkflowId={selectedId}
              onSelectWorkflow={handleSelectWorkflow}
              onCreateWorkflow={(input) =>
                createWorkflow.mutate(input, {
                  onSuccess: (wf: Workflow) => {
                    toast.success("Workflow created");
                    handleSelectWorkflow(wf.id);
                  },
                  onError: (e) =>
                    toast.error(
                      `Failed to create: ${e?.message || "Unknown error"}`,
                    ),
                })
              }
              onDeleteWorkflow={(id) => {
                deleteWorkflow.mutate(id, {
                  onSuccess: () => {
                    if (selectedId === id) handleSelectWorkflow(null);
                    toast.success("Deleted");
                  },
                });
              }}
              onUpdateWorkflow={(id, updates) => updateWorkflowMutation.mutate({ id, updates })}
              isUpdatingWorkflow={updateWorkflowMutation.isPending}
            />

            <main className="flex-1 bg-background relative flex flex-col">
              {selectedId ? (
                <WorkflowCanvas
                  workflowId={selectedId}
                  isSaving={saveWorkflowMutation.isPending}
                  onSave={handleSave}
                />
              ) : (
                // 5. UX: 空状态处理
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  Select or create a workflow to get started.
                </div>
              )}
            </main>
          </div>
        </div>
      </WorkflowProvider>
    </PageContainer>
  );
}
