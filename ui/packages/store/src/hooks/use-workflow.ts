import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, WorkflowSummary, type Workflow } from "@repo/api-client";

const ACTIVE_ID_KEY = ["active-workflow-id"];
const LS_ACTIVE_ID = "active-workflow-id";

export function useActiveWorkflowId() {
  return useQuery<string | null>({
    queryKey: ACTIVE_ID_KEY,
    queryFn: () =>
      typeof window !== "undefined" ? localStorage.getItem(LS_ACTIVE_ID) : null,
    initialData: () =>
      typeof window !== "undefined" ? localStorage.getItem(LS_ACTIVE_ID) : null,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}


export function useSetActiveWorkflowId() {
  const qc = useQueryClient();
  return React.useCallback(
    (id: string | null) => {
      console.log("Setting active workflow ID to:", id);
      if (typeof window !== "undefined") {
        if (id) localStorage.setItem(LS_ACTIVE_ID, id);
        else localStorage.removeItem(LS_ACTIVE_ID);
      }
      qc.setQueryData(ACTIVE_ID_KEY, id);
    },
    [qc]
  );
}

export function useSyncActiveWorkflowIdAcrossTabs() {
  const qc = useQueryClient();
  React.useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === LS_ACTIVE_ID) {
        qc.setQueryData(ACTIVE_ID_KEY, e.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [qc]);
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

/**
 * Returns the active workflow id, its summary (if present in the list),
 * and a setter. Falls back to fetching the workflow if not in the list.
 */
export function useActiveWorkflow() {
  const { data: activeId } = useActiveWorkflowId();
  const setActiveId = useSetActiveWorkflowId();

  const { data: list } = useWorkflowsList();

  // Prefer the summary from the list (stays fresh after rename/desc changes)
  const summaryFromList = React.useMemo(
    () => list?.find((w) => w.id === activeId) ?? null,
    [list, activeId]
  );

  // Optional fallback: if summary not in list, fetch the full workflow
  const { data: fetched } = useWorkflow(summaryFromList ? null : activeId);

  const summary: WorkflowSummary | null = React.useMemo(() => {
    if (summaryFromList) return summaryFromList;
    if (fetched) {
      // Adapt full Workflow -> WorkflowSummary shape if needed
      const { id, name, description } = fetched;
      return { id, name, description } as WorkflowSummary;
    }
    return null;
  }, [summaryFromList, fetched]);

  return {
    id: activeId,
    name: summary?.name || "default",
    summary,               // null until we can derive/fetch it
    setActiveId,           // (id: string | null) => void
  };
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

export interface WorkflowNodeCreate {
  /** Optional: let server generate if not a valid UUID */
  id?: string;
  measured: Record<string, number>;
  position: { x: number; y: number };
  selected: boolean;
  type: string;
  dragging: boolean;
  data: Record<string, any>;
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
    onSuccess: (wf: WorkflowSummary) => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      if (wf?.id) {
        qc.invalidateQueries({ queryKey: ["workflow", wf.id] });
      }
    },
  });
}


export function useDeleteWorkflow() {
  const qc = useQueryClient();
  const { data: activeId } = useActiveWorkflowId();
  const setActiveId = useSetActiveWorkflowId();

  return useMutation({
    mutationFn: api.dashboard.workflows.remove,
    onSuccess: (_ok, deletedId: string) => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      qc.removeQueries({ queryKey: ["workflow", deletedId] });
      if (activeId === deletedId) setActiveId(null);
    },
  });
}
