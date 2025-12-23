"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Save, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Accordion } from "@/components/ui/accordion";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FloatingActionButton } from "@/components/common/floating-action-button";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { useAssistants } from "@/features/assistants/hooks/use-assistants";
import { useAssistantEditor } from "@/features/assistants/hooks/use-assistant-editor";
import { CreateAssistantDialog } from "@/features/assistants/components/create-dialog";
import { AssistantItem } from "@/features/assistants/components/assistant-item";
import { PageContainer } from "@/components/common/page-container";

// Hooks

function CreateAssistantButton() {
  const params = useParams();
  const slug = params.slug as string;

  // 1. Data & API Logic
  const { assistantsQuery, createMutation, updateBatchMutation } =
    useAssistants(slug);

  // 2. Editor State Logic
  const { hasChanges, getDirtyAssistants } = useAssistantEditor(
    assistantsQuery.data,
  );

  // 3. UI State (Save Dialog)
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);

  const handleSave = async () => {
    await updateBatchMutation.mutateAsync(getDirtyAssistants());
    setSaveDialogOpen(false);
  };
  return (
    <FloatingActionButton>
      {/* Create Dialog */}
      <CreateAssistantDialog
        isPending={createMutation.isPending}
        onCreate={createMutation.mutate}
      />

      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogTrigger asChild>
          <Button disabled={!hasChanges}>
            <Save className="mr-2 h-4 w-4" /> Save Changes
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Changes</DialogTitle>
            <DialogDescription>
              Save configuration for all modified assistants?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:justify-end">
            <DialogClose asChild>
              <Button variant="outline">
                <X className="mr-2 h-4 w-4" /> Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSave}
              disabled={updateBatchMutation.isPending}
            >
              {updateBatchMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Confirm & Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </FloatingActionButton>
  );
}

export default function AssistantsPage() {
  const params = useParams();
  const slug = params.slug as string;

  // 1. Data & API Logic
  const {
    assistantsQuery,
    pluginsQuery,
    createMutation,
    deleteMutation,
    updateBatchMutation,
    addPluginMutation,
    removePluginMutation,
  } = useAssistants(slug);

  // 2. Editor State Logic
  const { editable, hasChanges, updateAssistant, getDirtyAssistants } =
    useAssistantEditor(assistantsQuery.data);

  return (
    <PageContainer
      title="Assistant Configuration"
      description="Manage assistants, plugins, and tool configurations."
      action={<CreateAssistantButton />}
    >
      {assistantsQuery.isLoading && <LoadingSkeleton lines={5} />}
      {assistantsQuery.isError && (
        <div className="text-red-600">Failed to load assistants.</div>
      )}

      {!assistantsQuery.isLoading &&
        !assistantsQuery.isError &&
        editable.length === 0 && (
          <EmptyState
            title="No assistants"
            description="Create one to get started."
          />
        )}

      <Accordion type="single" collapsible className="w-full space-y-4 pt-3">
        {editable.map((assistant, i) => (
          <AssistantItem
            key={assistant.id || i}
            assistant={assistant}
            plugins={pluginsQuery.data || []}
            onUpdate={(updated) => updateAssistant(i, updated)}
            onDelete={deleteMutation.mutate}
            isDeleting={
              deleteMutation.isPending &&
              deleteMutation.variables === assistant.id
            }
            pluginActions={{
              add: addPluginMutation.mutate,
              remove: removePluginMutation.mutate,
              isAdding: addPluginMutation.isPending,
              isRemoving: removePluginMutation.isPending,
              addingVars: addPluginMutation.variables,
              removingVars: removePluginMutation.variables,
            }}
          />
        ))}
      </Accordion>
    </PageContainer>
  );
}
