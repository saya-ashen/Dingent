import { useCallback } from "react";
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    BackgroundVariant,
    Panel,
    useReactFlow,
    type Node,
    type Connection,
    type NodeChange,
    type EdgeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "@/components/workflows/workflow-overrides.css";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { WorkflowNode, WorkflowEdge, Assistant } from "@/lib/types";

import AssistantNode from "./nodes/AssistantNode";
import DirectionalEdge from "./edges/DirectionalEdge";

const nodeTypes = {
    assistant: AssistantNode,
};

const edgeTypes = {
    directional: DirectionalEdge,
};

interface WorkflowEditorProps {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    onNodesChange: (changes: NodeChange<WorkflowNode>[]) => void;
    onEdgesChange: (changes: EdgeChange[]) => void;
    onConnect: (connection: Connection) => void;
    onNodeAdd: (node: WorkflowNode) => void;
    onSave: () => void;
    isSaving: boolean;
    onNodeContextMenu?: (event: React.MouseEvent, node: Node) => void;
    onPaneClick?: () => void;
}

export function WorkflowEditor({
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    onNodeAdd,
    onSave,
    isSaving,
    onNodeContextMenu,
    onPaneClick,
}: WorkflowEditorProps) {
    const { screenToFlowPosition } = useReactFlow();

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();
            const raw = event.dataTransfer.getData("application/reactflow");
            if (!raw) return;

            let assistant: Assistant | null = null;
            try {
                assistant = JSON.parse(raw);
            } catch {
                return;
            }
            if (!assistant) return;

            const position = screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode: WorkflowNode = {
                id: assistant.id,
                type: "assistant",
                position,
                data: {
                    assistantId: assistant.id,
                    assistantName: assistant.name,
                    description: assistant.description,
                },
            };

            onNodeAdd(newNode);
        },
        [screenToFlowPosition, onNodeAdd]
    );


    return (
        <div className="h-full border rounded-lg relative">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onNodeContextMenu={onNodeContextMenu}
                onPaneClick={onPaneClick}
                fitView
                panOnScroll
                selectionOnDrag
                panOnDrag={[1, 2]}
                zoomOnPinch
            >
                <Controls position="top-left" />
                <MiniMap
                    pannable
                    zoomable
                    style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}
                    nodeColor={(n) => (n.data?.isStart ? '#16a34a' : '#3b82f6')}
                />
                <Background
                    id="dots"
                    variant={BackgroundVariant.Dots}
                    gap={18}
                    size={1.4}
                    color="#cbd5e1"
                />
                <Panel position="top-right">
                    <Button onClick={onSave} disabled={isSaving} className="gap-2">
                        <Save size={16} />
                        {isSaving ? "Saving..." : "Save Workflow"}
                    </Button>
                </Panel>
            </ReactFlow>
        </div>
    );
}
