import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    BackgroundVariant,
    useNodesState,
    useEdgesState,
    addEdge,
    ReactFlowProvider,
    Panel,
    Handle,
    Position,
    type Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toast } from "sonner";
import { Plus, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { PageHeader } from "@/components/layout/Page";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { EmptyState } from "@/components/EmptyState";

import { getWorkflows, getAssistantsConfig, createWorkflow, saveWorkflow, deleteWorkflow } from "@/lib/api";
import type { Workflow, WorkflowNode, Assistant } from "@/lib/types";

// Custom Assistant Node Component
function AssistantNode({ data }: { data: { assistantName: string; description?: string } }) {
    return (
        <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-stone-400 min-w-[150px]">
            <Handle type="target" position={Position.Top} />
            <div className="flex">
                <div className="rounded-full w-3 h-3 bg-blue-500 border-2 border-gray-300 mr-2 mt-1"></div>
                <div className="ml-2">
                    <div className="text-lg font-bold">{data.assistantName}</div>
                    {data.description && (
                        <div className="text-gray-500 text-sm">{data.description}</div>
                    )}
                </div>
            </div>
            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}

const nodeTypes = {
    assistant: AssistantNode,
};

function WorkflowEditor({
    workflow,
    onSave,
    isSaving,
}: {
    workflow: Workflow;
    onSave: (workflow: Workflow) => void;
    isSaving: boolean;
}) {
    const [nodes, setNodes, onNodesChange] = useNodesState(workflow.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(workflow.edges);
    const reactFlowWrapper = useRef<HTMLDivElement>(null);
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            const type = event.dataTransfer.getData("application/reactflow");
            const assistantId = event.dataTransfer.getData("assistantId");
            const assistantName = event.dataTransfer.getData("assistantName");
            const description = event.dataTransfer.getData("description");

            if (typeof type === "undefined" || !type || !reactFlowInstance) {
                return;
            }

            const position = reactFlowInstance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode: WorkflowNode = {
                id: `${assistantId}-${Date.now()}`,
                type: "assistant",
                position,
                data: { assistantId, assistantName, description },
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance, setNodes]
    );

    const handleSave = () => {
        const updatedWorkflow: Workflow = {
            ...workflow,
            nodes,
            edges,
        };
        onSave(updatedWorkflow);
    };

    return (
        <div className="h-[600px] border rounded-lg">
            <ReactFlow
                ref={reactFlowWrapper}
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onInit={setReactFlowInstance}
                onDrop={onDrop}
                onDragOver={onDragOver}
                nodeTypes={nodeTypes}
                fitView
            >
                <Controls />
                <MiniMap />
                <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
                <Panel position="top-right">
                    <Button onClick={handleSave} disabled={isSaving} className="gap-2">
                        <Save size={16} />
                        {isSaving ? "Saving..." : "Save Workflow"}
                    </Button>
                </Panel>
            </ReactFlow>
        </div>
    );
}

function AssistantsPalette({ assistants }: { assistants: Assistant[] }) {
    const onDragStart = (event: React.DragEvent, assistant: Assistant) => {
        event.dataTransfer.setData("application/reactflow", "assistant");
        event.dataTransfer.setData("assistantId", assistant.id);
        event.dataTransfer.setData("assistantName", assistant.name);
        event.dataTransfer.setData("description", assistant.description || "");
        event.dataTransfer.effectAllowed = "move";
    };

    return (
        <div className="space-y-2">
            <h3 className="font-semibold">Assistants</h3>
            <p className="text-sm text-muted-foreground">Drag assistants to the workflow canvas</p>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {assistants.map((assistant) => (
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
                ))}
            </div>
        </div>
    );
}

function NewWorkflowDialog({ onCreateWorkflow }: { onCreateWorkflow: (name: string, description?: string) => void }) {
    const [open, setOpen] = useState(false);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (name.trim()) {
            onCreateWorkflow(name.trim(), description.trim() || undefined);
            setName("");
            setDescription("");
            setOpen(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button className="gap-2">
                    <Plus size={16} />
                    New Workflow
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Create New Workflow</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">Name</Label>
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Enter workflow name"
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="description">Description (Optional)</Label>
                        <Input
                            id="description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Enter workflow description"
                        />
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button type="submit">Create</Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}

export default function WorkflowsPage() {
    const qc = useQueryClient();
    const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);

    const workflowsQ = useQuery({
        queryKey: ["workflows"],
        queryFn: async () => (await getWorkflows()) ?? [],
        staleTime: 5_000,
    });

    const assistantsQ = useQuery({
        queryKey: ["assistants"],
        queryFn: async () => (await getAssistantsConfig()) ?? [],
        staleTime: 5_000,
    });

    const createWorkflowMutation = useMutation({
        mutationFn: async ({ name, description }: { name: string; description?: string }) =>
            createWorkflow(name, description),
        onSuccess: (newWorkflow) => {
            toast.success("Workflow created successfully");
            qc.invalidateQueries({ queryKey: ["workflows"] });
            setSelectedWorkflow(newWorkflow);
        },
        onError: (error) => {
            toast.error(`Failed to create workflow: ${error.message}`);
        },
    });

    const saveWorkflowMutation = useMutation({
        mutationFn: saveWorkflow,
        onSuccess: () => {
            toast.success("Workflow saved successfully");
            qc.invalidateQueries({ queryKey: ["workflows"] });
        },
        onError: (error) => {
            toast.error(`Failed to save workflow: ${error.message}`);
        },
    });

    const deleteWorkflowMutation = useMutation({
        mutationFn: deleteWorkflow,
        onSuccess: () => {
            toast.success("Workflow deleted successfully");
            qc.invalidateQueries({ queryKey: ["workflows"] });
            setSelectedWorkflow(null);
        },
        onError: (error) => {
            toast.error(`Failed to delete workflow: ${error.message}`);
        },
    });

    const handleCreateWorkflow = (name: string, description?: string) => {
        createWorkflowMutation.mutate({ name, description });
    };

    const handleSaveWorkflow = (workflow: Workflow) => {
        saveWorkflowMutation.mutate(workflow);
    };

    const handleDeleteWorkflow = (workflowId: string) => {
        deleteWorkflowMutation.mutate(workflowId);
    };

    if (workflowsQ.isLoading || assistantsQ.isLoading) {
        return <LoadingSkeleton lines={5} />;
    }

    if (workflowsQ.error || assistantsQ.error) {
        return <div className="text-red-600">Failed to load data.</div>;
    }

    const workflows = workflowsQ.data || [];
    const assistants = assistantsQ.data || [];

    return (
        <ReactFlowProvider>
            <PageHeader
                title="Workflows"
                description="Design and manage task handoff workflows between assistants"
                actions={<NewWorkflowDialog onCreateWorkflow={handleCreateWorkflow} />}
            />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Workflows List */}
                <div className="lg:col-span-1 space-y-4">
                    <div>
                        <h3 className="font-semibold mb-2">Workflows</h3>
                        {workflows.length === 0 ? (
                            <EmptyState
                                title="No workflows"
                                description="Create your first workflow to get started"
                            />
                        ) : (
                            <div className="space-y-2 max-h-[300px] overflow-y-auto">
                                {workflows.map((workflow) => (
                                    <div
                                        key={workflow.id}
                                        className={`p-3 border rounded cursor-pointer hover:bg-muted ${
                                            selectedWorkflow?.id === workflow.id ? "bg-primary/10 border-primary" : ""
                                        }`}
                                        onClick={() => setSelectedWorkflow(workflow)}
                                    >
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="font-medium">{workflow.name}</div>
                                                {workflow.description && (
                                                    <div className="text-sm text-muted-foreground">
                                                        {workflow.description}
                                                    </div>
                                                )}
                                            </div>
                                            <AlertDialog>
                                                <AlertDialogTrigger asChild>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="p-1 h-auto"
                                                        onClick={(e) => e.stopPropagation()}
                                                    >
                                                        <Trash2 size={14} />
                                                    </Button>
                                                </AlertDialogTrigger>
                                                <AlertDialogContent>
                                                    <AlertDialogTitle>Delete Workflow</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        Are you sure you want to delete "{workflow.name}"? This action cannot be undone.
                                                    </AlertDialogDescription>
                                                    <div className="flex justify-end gap-2">
                                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                        <AlertDialogAction onClick={() => handleDeleteWorkflow(workflow.id)}>
                                                            Delete
                                                        </AlertDialogAction>
                                                    </div>
                                                </AlertDialogContent>
                                            </AlertDialog>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Assistants Palette */}
                    {assistants.length > 0 && <AssistantsPalette assistants={assistants} />}
                </div>

                {/* Workflow Editor */}
                <div className="lg:col-span-3">
                    {selectedWorkflow ? (
                        <div className="space-y-4">
                            <div>
                                <h2 className="text-xl font-semibold">{selectedWorkflow.name}</h2>
                                {selectedWorkflow.description && (
                                    <p className="text-muted-foreground">{selectedWorkflow.description}</p>
                                )}
                            </div>
                            <WorkflowEditor
                                workflow={selectedWorkflow}
                                onSave={handleSaveWorkflow}
                                isSaving={saveWorkflowMutation.isPending}
                            />
                        </div>
                    ) : (
                        <EmptyState
                            title="No workflow selected"
                            description="Select a workflow from the list or create a new one to start designing"
                        />
                    )}
                </div>
            </div>
        </ReactFlowProvider>
    );
}