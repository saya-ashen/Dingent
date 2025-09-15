import type { Assistant } from "@repo/api-client";

export function AssistantsPalette({ assistants }: { assistants: Assistant[] }) {
  const onDragStart = (event: React.DragEvent, assistant: Assistant) => {
    event.dataTransfer.setData(
      "application/reactflow",
      JSON.stringify(assistant),
    );
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="space-y-2">
      <h3 className="font-semibold">Assistants</h3>
      <p className="text-sm text-muted-foreground">
        Drag to the workflow canvas
      </p>
      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
        {assistants.length > 0 ? (
          assistants.map((assistant) => (
            <div
              key={assistant.id}
              className="p-2 bg-muted rounded cursor-grab active:cursor-grabbing border"
              draggable
              onDragStart={(event) => onDragStart(event, assistant)}
            >
              <div className="font-medium">{assistant.name}</div>
              {assistant.description && (
                <div className="text-sm text-muted-foreground truncate">
                  {assistant.description}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="text-sm text-muted-foreground text-center py-4">
            All assistants are on the canvas.
          </div>
        )}
      </div>
    </div>
  );
}
