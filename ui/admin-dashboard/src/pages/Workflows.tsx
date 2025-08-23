import { useState, useEffect, useMemo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    ReactFlowProvider,
    applyNodeChanges,
    applyEdgeChanges,
    addEdge,
    type NodeChange,
    type EdgeChange,
    type Connection,
    type ReactFlowInstance,
} from "@xyflow/react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/Page";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { EmptyState } from "@/components/EmptyState";
import { WorkflowEditor } from "@/components/workflows/WorkflowEditor";
import { WorkflowList } from "@/components/workflows/WorkflowList";
import { AssistantsPalette } from "@/components/workflows/AssistantsPalette";
import { NewWorkflowDialog } from "@/components/workflows/NewWorkflowDialog";
import { getWorkflows, getAssistantsConfig, createWorkflow, saveWorkflow, deleteWorkflow } from "@/lib/api";
import type { Workflow, WorkflowNode, WorkflowEdge, Assistant } from "@/lib/types";

export default function WorkflowsPage() {
    const qc = useQueryClient();

    // State for the currently selected workflow object
    const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);

    // SINGLE SOURCE OF TRUTH for nodes and edges
    const [nodes, setNodes] = useState<WorkflowNode[]>([]);
    const [edges, setEdges] = useState<WorkflowEdge[]>([]);

    // --- Data Fetching ---
    const workflowsQ = useQuery({
        queryKey: ["workflows"],
        queryFn: async () => (await getWorkflows()) ?? [],
    });
    const assistantsQ = useQuery({
        queryKey: ["assistants"],
        queryFn: async () => (await getAssistantsConfig()) ?? [],
    });

    const workflows = workflowsQ.data || [];
    const allAssistants = assistantsQ.data || [];

    // --- State Synchronization ---
    // This effect synchronizes the local nodes/edges state when a different workflow is selected.
    useEffect(() => {
        if (selectedWorkflow) {
            // Use structuredClone to create a deep copy, preventing mutation of the cached data from react-query.
            setNodes(structuredClone(selectedWorkflow.nodes ?? []));
            setEdges(structuredClone(selectedWorkflow.edges ?? []));
        } else {
            // Clear the editor if no workflow is selected
            setNodes([]);
            setEdges([]);
        }
    }, [selectedWorkflow]);

    // --- Mutations ---
    const createWorkflowMutation = useMutation({
        mutationFn: ({ name, description }: { name: string; description?: string }) => createWorkflow(name, description),
        onSuccess: (newWorkflow) => {
            toast.success("Workflow created");
            qc.invalidateQueries({ queryKey: ["workflows"] });
            setSelectedWorkflow(newWorkflow);
        },
        onError: (error: Error) => toast.error(`Failed to create workflow: ${error.message}`),
    });

    const saveWorkflowMutation = useMutation({
        mutationFn: saveWorkflow,
        onSuccess: () => {
            toast.success("Workflow saved");
            qc.invalidateQueries({ queryKey: ["workflows"] });
        },
        onError: (error: Error) => toast.error(`Failed to save workflow: ${error.message}`),
    });

    // 1. 实现 onNodeAdd 逻辑
    const handleNodeAdd = useCallback((newNode: WorkflowNode) => {
        // 防止重复添加
        if (nodes.some(n => n.id === newNode.id)) {
            toast.warning("Assistant is already in the workflow.");
            return;
        }

        setNodes((nds) => nds.concat(newNode));

        // 自动连接到最右侧的节点
        if (nodes.length > 0) {
            const rightmostNode = nodes.reduce((prev, curr) => (prev.position.x > curr.position.x ? prev : curr));
            setEdges((eds) => addEdge({
                id: `e-${rightmostNode.id}-${newNode.id}`,
                source: rightmostNode.id,
                target: newNode.id,
            }, eds));
        }
    }, [nodes]); // 依赖于当前的 nodes



    const deleteWorkflowMutation = useMutation({
        mutationFn: deleteWorkflow,
        onSuccess: () => {
            toast.success("Workflow deleted");
            qc.invalidateQueries({ queryKey: ["workflows"] });
            setSelectedWorkflow(null); // Clear selection
        },
        onError: (error: Error) => toast.error(`Failed to delete workflow: ${error.message}`),
    });

    // --- Editor Logic Handlers ---

    const onNodesChange = useCallback((changes: NodeChange[]) => {
        // Prevent deletion of the 'start' node
        const filteredChanges = changes.filter(
            (change) => !(change.type === 'remove' && nodes.find(n => n.id === change.id)?.type === 'start')
        );
        setNodes((nds) => applyNodeChanges(filteredChanges, nds));
    }, [nodes]);

    const onEdgesChange = useCallback((changes: EdgeChange[]) => {
        setEdges((eds) => applyEdgeChanges(changes, eds));
    }, []);

    const onConnect = useCallback((connection: Connection) => {
        const sourceNode = nodes.find(n => n.id === connection.source);
        if (sourceNode?.type === 'start' && edges.some(e => e.source === sourceNode.id)) {
            toast.error("Start node can only have one outgoing connection.");
            return;
        }
        if (nodes.find(n => n.id === connection.target)?.type === 'start') {
            toast.error("Cannot connect into the Start node.");
            return;
        }
        setEdges((eds) => addEdge(connection, eds));
    }, [nodes, edges]);

    const onDrop = useCallback((event: React.DragEvent, reactFlowInstance: ReactFlowInstance) => {
        event.preventDefault();
        const assistant: Assistant = JSON.parse(event.dataTransfer.getData("application/reactflow"));
        if (!assistant || nodes.some(n => n.data?.assistantId === assistant.id)) {
            return; // Prevent adding duplicates
        }
        console.log("reactFlowInstance", reactFlowInstance)

        const position = reactFlowInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY });
        const newNode: WorkflowNode = {
            id: assistant.id, // Use assistant ID for uniqueness
            type: 'assistant',
            position,
            data: {
                assistantId: assistant.id,
                assistantName: assistant.name,
                description: assistant.description,
            },
        };

        setNodes((nds) => nds.concat(newNode));

        // Auto-connect to the nearest node
        const rightmostNode = nodes.reduce((prev, curr) => (prev.position.x > curr.position.x ? prev : curr), nodes[0]);
        if (rightmostNode) {
            setEdges((eds) => addEdge({
                id: `e-${rightmostNode.id}-${newNode.id}`,
                source: rightmostNode.id,
                target: newNode.id,
            }, eds));
        }
    }, [nodes]);

    const handleSaveWorkflow = () => {
        if (!selectedWorkflow) return;
        saveWorkflowMutation.mutate({
            ...selectedWorkflow,
            nodes, // Use the state from this component
            edges, // Use the state from this component
        });
    };

    // --- Derived State for UI ---
    // Calculate which assistants are available to be added to the canvas
    const paletteAssistants = useMemo(() => {
        const nodeAssistantIds = new Set(nodes.map(n => n.data?.assistantId).filter(Boolean));
        return allAssistants.filter((a) => !nodeAssistantIds.has(a.id));
    }, [allAssistants, nodes]);

    // --- Render Logic ---
    if (workflowsQ.isLoading || assistantsQ.isLoading) return <LoadingSkeleton lines={5} />;
    if (workflowsQ.error || assistantsQ.error) return <div className="text-red-600">Failed to load data.</div>;

    return (
        <ReactFlowProvider>
            <div className="flex flex-col h-[calc(100vh-4rem)]">
                <PageHeader
                    title="Workflows"
                    description="Design and manage task handoff workflows between assistants"
                />
                <div className="flex-1 min-h-0 w-full px-4 md:px-8 flex gap-8 mt-4">
                    {/* Left Sidebar */}
                    <aside className="w-full max-w-xs flex-shrink-0 flex flex-col gap-6">
                        <NewWorkflowDialog onCreateWorkflow={createWorkflowMutation.mutate} />
                        <WorkflowList
                            workflows={workflows}
                            selectedWorkflow={selectedWorkflow}
                            onSelect={setSelectedWorkflow}
                            onDelete={deleteWorkflowMutation.mutate}
                        />
                        <AssistantsPalette assistants={paletteAssistants} />
                    </aside>

                    {/* Main Editor Area */}
                    <main className="flex-1 min-h-0">
                        {selectedWorkflow ? (
                            <div className="h-full flex flex-col gap-4">
                                <div>
                                    <h2 className="text-xl font-semibold">{selectedWorkflow.name}</h2>
                                    {selectedWorkflow.description && (
                                        <p className="text-muted-foreground">{selectedWorkflow.description}</p>
                                    )}
                                </div>
                                // 调整为左右 ，Edge调整为双向
                                <div className="flex-1 min-h-0">
                                    <WorkflowEditor
                                        key={selectedWorkflow.id}
                                        nodes={nodes}
                                        edges={edges}
                                        onNodesChange={onNodesChange}
                                        onEdgesChange={onEdgesChange}
                                        onConnect={onConnect}
                                        onNodeAdd={handleNodeAdd} // 2. 传递新的回调函数
                                        onSave={handleSaveWorkflow}
                                        isSaving={saveWorkflowMutation.isPending}
                                    />
                                </div>
                            </div>
                        ) : (
                            <EmptyState
                                title="No workflow selected"
                                description="Select a workflow from the list or create a new one to start designing"
                            />
                        )}
                    </main>
                </div>
            </div>
        </ReactFlowProvider>
    );
}
