import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { type Workflow } from "@repo/api-client";
import type { AssistantsApi, WorkflowsApi } from "@repo/api-client";
import { workflowKeys } from "../queries/keys";
import { useWorkflowStore } from "../stores/workflow";
import { useEffect } from "react";

// --- Queries ---

export function useWorkflowsList(api: WorkflowsApi, workspaceId: string | undefined) {
  return useQuery({
    queryKey: workflowKeys.lists(workspaceId),
    enabled: !!workspaceId,
    queryFn: async () => (await api.list()) ?? [],
  });
}

export function useWorkflow(api: WorkflowsApi, id: string | null, workspaceId?: string) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: workflowKeys.detail(id!),
    enabled: !!id,
    queryFn: async () => api.get(id!),
    placeholderData: () => {
      if (!workspaceId) return undefined;
      const list = queryClient.getQueryData<Workflow[]>(workflowKeys.lists(workspaceId));
      return list?.find((w) => w.id === id);
    },
  });
}

export function useAssistantsConfig(api: AssistantsApi, workspaceId: string | undefined) {
  return useQuery({
    queryKey: workflowKeys.assistants(workspaceId),
    enabled: !!workspaceId,
    queryFn: async () => (await api.list()) ?? [],
  });
}


export function useActiveWorkflow(api: WorkflowsApi, workspaceId: string | undefined) {
  const { activeId, setActiveId } = useWorkflowStore();

  const { data: workflow, isLoading, isError } = useWorkflow(api, activeId, workspaceId);

  useEffect(() => {
    if (workspaceId && workflow && workflow.workspaceId !== workspaceId) {
      // 如果后端返回了 workflow 的 workspaceId 字段，可以在这里做校验重置
      // 或者更简单地：在 workspaceId 变化的 useEffect 中重置 store
      setActiveId(null);
    }
  }, [workspaceId, setActiveId]); // 注意：这里逻辑取决于你具体的切换时机

  return {
    id: activeId,
    workflow,
    isLoading,
    isError,
    setActiveId,
    name: workflow?.name || "Untitled",
  };
}

// --- Mutations ---

export function useCreateWorkflow(api: WorkflowsApi, workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  const { setActiveId } = useWorkflowStore();

  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) => {
      if (!workspaceId) throw new Error("No workspace selected");
      return api.create({ name, description });
    },
    onSuccess: (newWf) => {
      // 1. 仅使得当前 Workspace 的列表过期
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists(workspaceId) });

      // 2. 写入详情缓存
      queryClient.setQueryData(workflowKeys.detail(newWf.id), newWf);

      // 3. 自动设为当前选中
      setActiveId(newWf.id);
    },
  });
}

export function useSaveWorkflow(api: WorkflowsApi, workspaceId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Workflow) => api.update(data),
    onSuccess: (savedWf) => {
      // 更新当前 Workspace 的列表缓存（例如名称变更）
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists(workspaceId) });

      if (savedWf?.id) {
        queryClient.invalidateQueries({ queryKey: workflowKeys.detail(savedWf.id) });
      }
    },
  });
}

export function useDeleteWorkflow(api: WorkflowsApi, workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  const { activeId, setActiveId } = useWorkflowStore();

  return useMutation({
    mutationFn: (id: string) => api.delete(id),
    onSuccess: (_ok, deletedId) => {
      // 更新当前 Workspace 的列表
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists(workspaceId) });
      queryClient.removeQueries({ queryKey: workflowKeys.detail(deletedId) });

      if (activeId === deletedId) {
        setActiveId(null);
      }
    },
  });
}
