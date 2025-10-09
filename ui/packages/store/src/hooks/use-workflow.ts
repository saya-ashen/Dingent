import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, WorkflowSummary, type Workflow } from "@repo/api-client";

const KEY = ["active-workflow-id"];
const LS_KEY = "active-workflow-id";

export function useActiveWorkflowId() {
  return useQuery<string | null>({
    queryKey: KEY,
    initialData: () =>
      typeof window !== "undefined" ? localStorage.getItem(LS_KEY) : null,
  });
}

export function useSetActiveWorkflowId() {
  const qc = useQueryClient();
  return React.useCallback(
    (id: string | null) => {
      if (typeof window !== "undefined") {
        if (id) localStorage.setItem(LS_KEY, id);
        else localStorage.removeItem(LS_KEY);
      }
      qc.setQueryData(KEY, id);
    },
    [qc]
  );
}

export function useWorkflow(id: string | null) {
  return useQuery<Workflow | null>({
    queryKey: ["workflow", id],
    enabled: !!id,
    queryFn: async () => {
      if (!id) return null;
      return api.dashboard.workflows.get(id);
    },
  });
}

export function useWorkflowsList() {
  return useQuery<WorkflowSummary[]>({
    queryKey: ["workflows"],
    queryFn: async () => (await api.dashboard.workflows.list()) ?? [],
  });
}

export function useAssistantsConfig() {
  return useQuery({
    queryKey: ["assistants"],
    queryFn: async () =>
      (await api.dashboard.assistants.getAssistantsConfig()) ?? [],
  });
}


export function useCreateWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      api.dashboard.workflows.create(name, description),
    onSuccess: (wf: Workflow) => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      qc.setQueryData(["workflow", wf.id], wf);
    },
  });
}


export function useSaveWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.dashboard.workflows.save,
    onSuccess: (wf: Workflow) => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      if (wf?.id) qc.setQueryData(["workflow", wf.id], wf);
    },
  });
}


export function useDeleteWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.dashboard.workflows.remove,
    onSuccess: (_ok, deletedId: string) => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      qc.removeQueries({ queryKey: ["workflow", deletedId] });
    },
  });
}
