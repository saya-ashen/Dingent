import { useCallback } from "react";
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    BackgroundVariant,
    Handle,
    Position,
    Panel,
    useReactFlow, // 1. 导入 useReactFlow Hook
    type Node,
    type Edge,
    type Connection,
    type NodeChange,
    type EdgeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { WorkflowNode, WorkflowEdge, Assistant } from "@/lib/types";

// Custom Node for "Start"
function StartNode() {
    return (
        <div className="px-4 py-2 rounded-full bg-emerald-500 text-white text-sm font-semibold shadow border border-emerald-600">
            Start
            <Handle
                type="source"
                position={Position.Bottom}
                className="!bg-white !w-3 !h-3 !border-emerald-600"
            />
        </div>
    );
}

// Custom Node for Assistants
function AssistantNode({ data }: { data: { assistantName: string; description?: string } }) {
    return (
        <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-stone-400 min-w-[150px]">
            {/* An assistant can be both a target and a source */}
            <Handle type="target" position={Position.Top} />
            <div className="flex items-center">
                <div className="rounded-full w-3 h-3 bg-blue-500 border-2 border-gray-300 mr-2" />
                <div className="ml-2">
                    <div className="text-lg font-bold">{data.assistantName}</div>
                    {data.description && <div className="text-gray-500 text-sm">{data.description}</div>}
                </div>
            </div>
            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}

const nodeTypes = {
    start: StartNode,
    assistant: AssistantNode,
};

export function WorkflowEditor({
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    onNodeAdd, // 2. 接收一个新的回调函数
    onSave,
    isSaving,
}: {
    nodes: Node<WorkflowNode["data"]>[];
    edges: Edge<WorkflowEdge["data"]>[];
    onNodesChange: (changes: NodeChange[]) => void;
    onEdgesChange: (changes: EdgeChange[]) => void;
    onConnect: (connection: Connection) => void;
    onNodeAdd: (node: WorkflowNode) => void; // 3. 定义新回调的类型
    onSave: () => void;
    isSaving: boolean;
}) {
    // 4. 安全地获取 React Flow 实例
    const { screenToFlowPosition } = useReactFlow();

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
    }, []);

    // 5. 将 onDrop 逻辑移到这里
    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            const assistant: Assistant = JSON.parse(event.dataTransfer.getData("application/reactflow"));
            if (!assistant) {
                return;
            }

            // 使用从 hook 中获取的方法，这是稳定可靠的
            const position = screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode: WorkflowNode = {
                id: assistant.id,
                type: 'assistant',
                position,
                data: {
                    assistantId: assistant.id,
                    assistantName: assistant.name,
                    description: assistant.description,
                },
            };

            // 6. 调用父组件传递过来的函数来更新状态
            onNodeAdd(newNode);
        },
        [screenToFlowPosition, onNodeAdd]
    );

    return (
        <div className="h-full border rounded-lg">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onDrop={onDrop} // 使用在组件内部定义的 onDrop
                onDragOver={onDragOver}
                nodeTypes={nodeTypes}
                fitView
            >
                <Controls />
                <MiniMap />
                <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
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
