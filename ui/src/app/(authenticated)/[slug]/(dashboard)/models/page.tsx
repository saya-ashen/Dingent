"use client";

import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageContainer } from "@/components/common/page-container";
import { useModels } from "@/features/models/hooks/use-models";
import { ModelConfigDialog } from "@/features/models/components/model-config-dialog";
import { ModelsTable } from "@/features/models/components/models-table";
import type { TestConnectionRequest } from "@/types/entity";

export default function ModelsPage() {
  const params = useParams();
  const slug = params.slug as string;

  const {
    modelsQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    testConnectionMutation,
  } = useModels(slug);

  const handleTestConnection = async (data: TestConnectionRequest) => {
    const result = await testConnectionMutation.mutateAsync(data);
    return result;
  };

  return (
    <PageContainer
      title="Model Configuration"
      description="Manage LLM model configurations for your workspace."
      action={
        <ModelConfigDialog
          isPending={createMutation.isPending}
          onSave={createMutation.mutate}
          onTestConnection={handleTestConnection}
        />
      }
    >
      {modelsQuery.isLoading && <LoadingSkeleton lines={5} />}
      
      {modelsQuery.isError && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-red-600">Failed to load model configurations.</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => modelsQuery.refetch()}
          >
            Retry
          </Button>
        </div>
      )}

      {!modelsQuery.isLoading && !modelsQuery.isError && (
        <ModelsTable
          models={modelsQuery.data || []}
          onEdit={(id, data) => updateMutation.mutate({ id, data })}
          onDelete={deleteMutation.mutate}
          onTestConnection={handleTestConnection}
          isUpdating={updateMutation.isPending}
          isDeleting={deleteMutation.isPending}
          deletingId={deleteMutation.variables}
        />
      )}
    </PageContainer>
  );
}
