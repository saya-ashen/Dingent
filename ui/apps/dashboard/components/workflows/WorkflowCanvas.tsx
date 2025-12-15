"use client";
import { useEffect, useState, useRef } from "react";
import { ReactFlow, ReactFlowProvider, Background, Controls, Panel } from "@xyflow/react";
import { useFlowLogic } from "./hooks/useFlowLogic";
import { useWorkflowContext } from "./WorkflowContext";
import { Button, LoadingSkeleton } from "@repo/ui/components";
import { Save } from "lucide-react";
import { nodeTypes } from "./nodes";
import { edgeTypes } from "./edges";

import { useWorkflow } from "@repo/store";
import { normalizeWorkflow } from "@/lib/workflows-normalize";
import "@xyflow/react/dist/style.css";
import { getClientApi } from "@/lib/api/client";
import { useParams } from "next/navigation";

interface CanvasProps {
  workflowId: string | null;
  onSave: (nodes: any[], edges: any[]) => void;
  isSaving: boolean;
}

function WorkflowCanvasContent({ workflowId, onSave, isSaving }: CanvasProps) {
  const params = useParams();
  const slug = params.slug as string;
  const api = getClientApi();
  const wfApi = api.forWorkspace(slug).workflows;
  const { draggedAssistant, setUsedAssistantIds } = useWorkflowContext();
  const { data: workflowData, isLoading } = useWorkflow(wfApi, workflowId);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // 本地状态
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);

  // 1. 初始化数据 (Hydration)
  useEffect(() => {
    if (workflowData) {
      const { nodes: initNodes, edges: initEdges } = normalizeWorkflow(workflowData);
      setNodes(initNodes);
      setEdges(initEdges);
    }
  }, [workflowData]);
  useEffect(() => {
    const ids = new Set(
      nodes
        .map((n) => n.data?.assistantId as string)
        .filter(Boolean)
    );
    setUsedAssistantIds(ids);
  }, [nodes, setUsedAssistantIds]);

  // 2. 引入逻辑 Hook
  const { onNodesChange, onEdgesChange, onConnect, onDrop } = useFlowLogic(nodes, setNodes, edges, setEdges);

  // 处理 DragOver，必须允许 drop
  const onDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  };
  if (!workflowId) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Select a workflow to start editing</div>;
  }

  if (isLoading) {
    return <div className="flex h-full items-center justify-center"><LoadingSkeleton /></div>;
  }


  return (
    <div className="h-full w-full relative" ref={wrapperRef}>
      <Button
        onClick={() => onSave(nodes, edges)}
        disabled={isSaving}
        size="sm"
      >
        <Save className="mr-2 h-4 w-4" />
        {isSaving ? "Saving..." : "Save Workflow"}
      </Button>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={(e) => onDrop(e, draggedAssistant)}
        onDragOver={onDragOver}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

// 必须包裹 ReactFlowProvider 才能在内部使用 useReactFlow (在 hooks 里)
export function WorkflowCanvas(props: CanvasProps) {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasContent {...props} />
    </ReactFlowProvider>
  );
}
