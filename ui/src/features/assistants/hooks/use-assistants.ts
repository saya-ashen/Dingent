"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getClientApi } from "@/lib/api/client";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/utils";

export function useAssistants(workspaceSlug: string) {
  const qc = useQueryClient();
  const api = getClientApi();
  const wsApi = api.forWorkspace(workspaceSlug);

  // Queries
  const assistantsQuery = useQuery({
    queryKey: ["assistants", workspaceSlug],
    queryFn: async () => (await wsApi.assistants.list()) ?? [],
    staleTime: 5_000,
  });

  const pluginsQuery = useQuery({
    queryKey: ["available-plugins", workspaceSlug],
    queryFn: async () => (await wsApi.plugins.list()) ?? [],
    staleTime: 30_000,
  });

  const modelsQuery = useQuery({
    queryKey: ["models", workspaceSlug],
    queryFn: async () => (await wsApi.models.list()) ?? [],
    staleTime: 30_000,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      wsApi.assistants.create(data),
    onSuccess: () => {
      toast.success("Assistant added successfully!");
      qc.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Add assistant failed")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => wsApi.assistants.delete(id),
    onSuccess: () => {
      toast.success("Assistant deleted");
      qc.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Delete assistant failed")),
  });

  const updateBatchMutation = useMutation({
    mutationFn: async (assistants: any[]) => {
      await Promise.all(
        assistants.map((a) => wsApi.assistants.update(a.id, a))
      );
    },
    onSuccess: () => {
      toast.success("All changes saved!");
      qc.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to save changes")),
  });

  const addPluginMutation = useMutation({
    mutationFn: (p: { assistantId: string; pluginId: string }) =>
      wsApi.assistants.addPlugin(p.assistantId, p.pluginId),
    onSuccess: () => {
      toast.success("Plugin added");
      qc.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Add plugin failed")),
  });

  const removePluginMutation = useMutation({
    mutationFn: (p: { assistantId: string; pluginId: string }) =>
      wsApi.assistants.removePlugin(p.assistantId, p.pluginId),
    onSuccess: () => {
      toast.success("Plugin removed");
      qc.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (e) => toast.error(getErrorMessage(e, "Remove plugin failed")),
  });

  return {
    assistantsQuery,
    pluginsQuery,
    modelsQuery,
    createMutation,
    deleteMutation,
    updateBatchMutation,
    addPluginMutation,
    removePluginMutation,
  };
}
