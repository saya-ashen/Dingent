import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { WorkflowSummary, type Workflow } from "@repo/api-client";
import type { AssistantsApi, WorkflowsApi } from "@repo/api-client";
import { workflowKeys } from "../queries/keys";
import { useWorkflowStore } from "../stores/workflow";

// --- Queries ---

export function useWorkflowsList(api: WorkflowsApi) {
  return useQuery({
    queryKey: workflowKeys.lists(),
    queryFn: async () => (await api.list()) ?? [],
  });
}

export function useWorkflow(api: WorkflowsApi, id: string | null) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: workflowKeys.detail(id!),
    enabled: !!id,
    queryFn: async () => api.get(id!),
    placeholderData: () => {
      const list = queryClient.getQueryData<Workflow[]>(workflowKeys.lists());
      return list?.find((w) => w.id === id);
    },
  });
}

export function useAssistantsConfig(api: AssistantsApi) {
  return useQuery({
    queryKey: workflowKeys.assistants,
    queryFn: async () => (await api.list()) ?? [],
  });
}

// --- Composite Hook (结合 Zustand 和 React Query) ---

export function useActiveWorkflow(api: WorkflowsApi) {
  const { activeId, setActiveId } = useWorkflowStore();

  // 获取详情（如果缓存里有列表数据，会自动作为初始数据展示）
  const { data: workflow, isLoading, isError } = useWorkflow(api, activeId);

  return {
    id: activeId,
    workflow, // 可能是 Full Workflow 或 Summary (取决于 placeholderData)
    isLoading,
    isError,
    setActiveId,
    // 辅助属性，防止 workflow 为空时报错
    name: workflow?.name || "Untitled",
  };
}

// --- Mutations ---

export function useCreateWorkflow(api: WorkflowsApi) {
  const queryClient = useQueryClient();
  const { setActiveId } = useWorkflowStore();

  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      api.create({ name, description }),
    onSuccess: (newWf) => {
      // 1. 更新列表缓存
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      // 2. 写入详情缓存 (避免由于重定向导致的二次 fetch)
      queryClient.setQueryData(workflowKeys.detail(newWf.id), newWf);
      // 3. 自动设为当前选中
      setActiveId(newWf.id);
    },
  });
}

export function useSaveWorkflow(api: WorkflowsApi) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Workflow) => api.update(data),
    onSuccess: (savedWf) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });

      if (savedWf?.id) {
        queryClient.invalidateQueries({ queryKey: workflowKeys.detail(savedWf.id) });
      }
    },
  });
}

export function useDeleteWorkflow(api: WorkflowsApi) {
  const queryClient = useQueryClient();
  const { activeId, setActiveId } = useWorkflowStore();

  return useMutation({
    mutationFn: (id: string) => api.delete(id),
    onSuccess: (_ok, deletedId) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.lists() });
      queryClient.removeQueries({ queryKey: workflowKeys.detail(deletedId) });

      // 如果删除的是当前选中的，清除选中状态
      if (activeId === deletedId) {
        setActiveId(null);
      }
    },
  });
}
