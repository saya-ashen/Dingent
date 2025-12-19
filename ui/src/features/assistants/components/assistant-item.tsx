import { AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { StatusBadge } from "@/components/common/status-badge";
import { AssistantEditor } from "@/features/assistants/components/plugin-editor";
import { Assistant } from "@/types/entity";
import { Loader2 } from "lucide-react";
import { safeBool, effectiveStatusForItem } from "@/lib/utils";

interface AssistantItemProps {
  assistant: Assistant;
  plugins: any[]; // Replace with Plugin type
  onUpdate: (updated: Assistant) => void;
  onDelete: (id: string) => void;
  isDeleting: boolean;
  pluginActions: {
    add: (vars: { assistantId: string; pluginId: string }) => void;
    remove: (vars: { assistantId: string; pluginId: string }) => void;
    isAdding: boolean;
    isRemoving: boolean;
    addingVars?: { pluginId: string };
    removingVars?: { pluginId: string };
  };
}

export function AssistantItem({
  assistant,
  plugins,
  onUpdate,
  onDelete,
  isDeleting,
  pluginActions
}: AssistantItemProps) {
  const enabled = safeBool(assistant.enabled, false);
  const { level, label } = effectiveStatusForItem(assistant.status, enabled);

  return (
    <AccordionItem value={assistant.id} className="rounded-lg border">
      <AccordionTrigger className="px-4 py-3 text-lg font-semibold hover:no-underline">
        <div className="flex w-full items-center justify-between gap-4 pr-4">
          <span className="truncate">{assistant.name || "Unnamed"}</span>
          <StatusBadge level={level} label={label} title={assistant.status} />
        </div>
      </AccordionTrigger>
      <AccordionContent className="p-4 pt-0">
        <div className="mb-4 flex justify-end">
          <ConfirmDialog
            title="Confirm Delete"
            description={`Delete '${assistant.name}'?`}
            confirmText="Delete"
            onConfirm={() => onDelete(assistant.id)}
            trigger={
              <Button variant="destructive" size="sm" disabled={isDeleting}>
                {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Delete Assistant
              </Button>
            }
          />
        </div>
        <AssistantEditor
          assistant={assistant}
          onChange={onUpdate}
          availablePlugins={plugins}
          onAddPlugin={(pluginId) => pluginActions.add({ assistantId: assistant.id, pluginId })}
          isAddingPlugin={pluginActions.isAdding}
          addingPluginDetails={pluginActions.addingVars}
          onRemovePlugin={(pluginId) => pluginActions.remove({ assistantId: assistant.id, pluginId })}
          isRemovingPlugin={pluginActions.isRemoving}
          removingPluginDetails={pluginActions.removingVars}
        />
      </AccordionContent>
    </AccordionItem>
  );
}
