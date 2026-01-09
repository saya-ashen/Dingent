"use client";
import { useMemo, useState } from "react";
import { WorkflowList } from "../components/WorkflowList";
import { GripVertical } from "lucide-react";
import { TabsList, TabsTrigger, TabsContent, Tabs } from "@/components/ui/tabs";
import { Assistant } from "@/types/entity";
import { useWorkflowContext } from "../providers";
import { NewWorkflowDialog } from "./workflows/NewWorkflowDialog";

interface SidebarProps {
  workflows: any[];
  assistants: Assistant[];
  models?: any[];
  selectedWorkflowId: string | null;
  onSelectWorkflow: (id: string | null) => void;
  onCreateWorkflow: (input: { name: string; description?: string }) => void;
  onDeleteWorkflow: (id: string) => void;
  onUpdateWorkflow?: (id: string, updates: any) => void;
  isUpdatingWorkflow?: boolean;
}

export function WorkflowSidebar({
  workflows,
  assistants,
  models = [],
  selectedWorkflowId,
  onSelectWorkflow,
  onCreateWorkflow,
  onDeleteWorkflow,
  onUpdateWorkflow,
  isUpdatingWorkflow,
}: SidebarProps) {
  const { setDraggedAssistant, usedAssistantIds } = useWorkflowContext();
  const [activeTab, setActiveTab] = useState("workflows");

  // 当选中工作流时，自动切到 components tab，提升体验
  const handleSelect = (wf: any) => {
    onSelectWorkflow(wf.id);
    setActiveTab("components");
  };
  const handleDeleteWorkflow = (id: string) => {
    onDeleteWorkflow(id);
  };

  const availableAssistants = useMemo(() => {
    return assistants.filter((a) => !usedAssistantIds.has(a.id));
  }, [assistants, usedAssistantIds]);

  const onDragStart = (event: React.DragEvent, assistant: Assistant) => {
    setDraggedAssistant(assistant);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="flex w-80 flex-col border-r bg-muted/10 h-full">
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex flex-col h-full"
      >
        <div className="px-4 pt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="workflows">Workflows</TabsTrigger>
            <TabsTrigger value="components" disabled={!selectedWorkflowId}>
              Components
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="workflows" className="flex-1 overflow-auto p-4">
          <div className="shrink-0">
            <NewWorkflowDialog onCreateWorkflow={onCreateWorkflow} />
          </div>
          <WorkflowList
            workflows={workflows}
            selectedWorkflow={workflows.find(
              (w) => w.id === selectedWorkflowId,
            )}
            models={models}
            onSelect={handleSelect}
            onDelete={handleDeleteWorkflow}
            onUpdateWorkflow={onUpdateWorkflow}
            isUpdating={isUpdatingWorkflow}
          />
        </TabsContent>

        {/* Tab 2: Components (Draggable) */}
        <TabsContent
          value="components"
          className="flex-1 overflow-auto p-4 space-y-3"
        >
          <div className="text-sm text-muted-foreground mb-4">
            Drag assistants to the canvas to build your flow.
          </div>
          {availableAssistants.length > 0 ? (
            availableAssistants.map((assistant) => (
              <div
                key={assistant.id}
                draggable
                onDragStart={(e) => onDragStart(e, assistant)}
                className="flex items-center gap-3 p-3 bg-card border rounded-md cursor-grab active:cursor-grabbing hover:border-primary transition-colors shadow-sm"
              >
                <GripVertical className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium text-sm">{assistant.name}</div>
                  <div className="text-xs text-muted-foreground line-clamp-1">
                    {assistant.description || "No description"}
                  </div>
                </div>
              </div>
            ))
          ) : (
            // 处理空状态：所有助手都用完了
            <div className="text-center text-sm text-muted-foreground py-8 border border-dashed rounded-md">
              All available assistants are currently in use.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
