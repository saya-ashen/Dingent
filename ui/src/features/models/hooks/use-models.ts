"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getClientApi } from "@/lib/api/client";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/utils";
import type {
  LLMModelConfigCreate,
  LLMModelConfigUpdate,
  TestConnectionRequest,
} from "@/types/entity";

export function useModels(workspaceSlug: string) {
  const qc = useQueryClient();
  const api = getClientApi();
  const wsApi = api.forWorkspace(workspaceSlug);

  // Queries
  const modelsQuery = useQuery({
    queryKey: ["models", workspaceSlug],
    queryFn: async () => (await wsApi.models.list()) ?? [],
    staleTime: 5_000,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: LLMModelConfigCreate) => wsApi.models.create(data),
    onSuccess: () => {
      toast.success("Model configuration added successfully!");
      qc.invalidateQueries({ queryKey: ["models"] });
    },
    onError: (e) =>
      toast.error(getErrorMessage(e, "Add model configuration failed")),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: LLMModelConfigUpdate }) =>
      wsApi.models.update(id, data),
    onSuccess: () => {
      toast.success("Model configuration updated!");
      qc.invalidateQueries({ queryKey: ["models"] });
    },
    onError: (e) =>
      toast.error(getErrorMessage(e, "Update model configuration failed")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => wsApi.models.delete(id),
    onSuccess: () => {
      toast.success("Model configuration deleted");
      qc.invalidateQueries({ queryKey: ["models"] });
    },
    onError: (e) =>
      toast.error(getErrorMessage(e, "Delete model configuration failed")),
  });

  const testConnectionMutation = useMutation({
    mutationFn: (data: TestConnectionRequest) =>
      wsApi.models.testConnection(data),
    onError: (e) =>
      toast.error(getErrorMessage(e, "Test connection failed")),
  });

  return {
    modelsQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    testConnectionMutation,
  };
}
