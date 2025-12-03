"use client";
import { useEffect, useMemo, useCallback, useRef, useState } from "react";
import {
  ReactFlowProvider,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from "@xyflow/react";
import { toast } from "sonner";
import { WorkflowEditor, ContextMenu, EmptyState, LoadingSkeleton } from "@repo/ui/components";
import type { Workflow, WorkflowNode, WorkflowEdge } from "@repo/api-client";
import { normalizeWorkflow } from "../../lib/workflows-normalize";
import { useWorkflow } from "@repo/store";

interface EditorPanelProps {
  workflowId: string | null;
  onSave: (wf: Workflow) => void;
  isSaving: boolean;
  onNodeAssistantIdsChange?: (ids: Set<string>) => void;
}

export function WorkflowEditorPanel({
  workflowId,
  onSave,
  isSaving,
  onNodeAssistantIdsChange,
}: EditorPanelProps) {
  const editorWrapperRef = useRef<HTMLDivElement | null>(null);
  const [menu, setMenu] = useState<null | { id: string; x: number; y: number }>(null);

  const { data: wf, isLoading, error } = useWorkflow(workflowId);
  const [{ nodes, edges }, setGraph] = useState<{ nodes: WorkflowNode[]; edges: WorkflowEdge[] }>({ nodes: [], edges: [] });

  // hydrate graph from the full workflow
  useEffect(() => {
    const { nodes, edges } = normalizeWorkflow(wf ?? null);
    setGraph({ nodes, edges });
    if (onNodeAssistantIdsChange) {
      const ids = new Set(
        nodes.map((n) => n?.data?.assistantId).filter(Boolean)
      );
      onNodeAssistantIdsChange(ids);
    }
  }, [wf, onNodeAssistantIdsChange]);

  const setNodes = useCallback(
    (updater: (prev: WorkflowNode[]) => WorkflowNode[]) =>
      setGraph((g) => ({ ...g, nodes: updater(g.nodes) })),
    [],
  );
  const setEdges = useCallback(
    (updater: (prev: WorkflowEdge[]) => WorkflowEdge[]) =>
      setGraph((g) => ({ ...g, edges: updater(g.edges) })),
    [],
  );

  const onNodesChange = useCallback(
    (changes: NodeChange<WorkflowNode>[]) => {
      const removeChanges = changes.filter(
        (change) => change.type === "remove" && nodes.find((n) => n.id === change.id)?.data?.isStart,
      );
      if (removeChanges.length > 0) {
        toast.warning("The Start node cannot be deleted.");
        return;
      }
      setNodes((nds) => applyNodeChanges<WorkflowNode>(changes, nds));
    },
    [nodes, setNodes],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setEdges((currentEdges) => {
        const nextEdges = applyEdgeChanges(changes, currentEdges);
        return nextEdges;
      });
    },
    [setEdges],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      const { source, target } = connection;
      if (!source || !target) return;
      if (source === target) return;

      setEdges((prev) => {
        const existing = prev.find(
          (e) =>
            (e.source === source && e.target === target) ||
            (e.source === target && e.target === source),
        );
        if (!existing) {
          const newEdge: WorkflowEdge = {
            id: `${source}>>>${target}`,
            source,
            target,
            sourceHandle: connection.sourceHandle,
            targetHandle: connection.targetHandle,
            type: "directional",
            data: { mode: "single" },
          };
          return addEdge(newEdge, prev);
        }
        if (existing.source === source && existing.target === target) {
          if ((existing).data?.mode === "bidirectional") {
            toast.warning("This pair is already bidirectional.");
            return prev;
          }
          toast.warning("A connection in this direction already exists.");
          return prev;
        }
        if ((existing).data?.mode !== "bidirectional") {
          return prev.map((e) =>
            e.id === existing.id
              ? { ...e, data: { ...(e.data || {}), mode: "bidirectional" } }
              : e,
          );
        }
        return prev;
      });
    },
    [setEdges],
  );

  const handleNodeAdd = useCallback((newNode: WorkflowNode) => {
    setNodes((prev) => {
      if (prev.some((n) => n.id === newNode.id)) {
        toast.warning("Assistant is already in the workflow.");
        return prev;
      }
      const isFirst = prev.length === 0;
      const node: WorkflowNode = {
        ...newNode,
        type: "assistant",
        data: {
          ...(newNode.data || {}),
          isStart: isFirst,
        },
      };
      return [...prev, node];
    });
  }, [setNodes]);

  const setStartNode = useCallback((id: string) => {
    setNodes((prev) => {
      if (!prev.some((n) => n.id === id)) return prev;
      return prev.map((n) => ({
        ...n,
        data: {
          ...(n.data || {}),
          isStart: n.id === id,
        },
      }));
    });
  }, [setNodes]);

  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: { id: string }) => {
      event.preventDefault();
      setMenu({ id: node.id, x: event.clientX, y: event.clientY });
    },
    [],
  );

  const onPaneClick = useCallback(() => setMenu(null), []);

  const deleteNode = (id: string) => {
    const target = nodes.find((n) => n.id === id);
    if (target?.data?.isStart) {
      toast.warning("The Start node cannot be deleted.");
      setMenu(null);
      return;
    }
    setNodes((ns) => ns.filter((node) => node.id !== id));
    setEdges((es) => es.filter((e) => e.source !== id && e.target !== id));
    setMenu(null);
  };

  const handleSave = () => {
    if (!wf) return;
    onSave({ ...wf, nodes, edges });
  };

  const contextMenuItems = useMemo(() => {
    if (!menu) return [];
    const node = nodes.find((n) => n.id === menu.id);
    const isStart = node?.data?.isStart;
    return [
      {
        key: "set-start",
        label: isStart ? "Already Start Node" : "Set as Start Node",
        disabled: !!isStart,
        onClick: (id: string) => setStartNode(id),
      },
      {
        key: "delete",
        label: "Delete Node",
        danger: true,
        disabled: isStart,
        onClick: deleteNode,
      },
    ];
  }, [menu, nodes, setStartNode]);

  if (!workflowId) {
    return (
      <EmptyState
        title="No workflow selected"
        description="Select a workflow from the list or create a new one to start designing"
      />
    );
  }

  if (isLoading) return <LoadingSkeleton lines={8} />;
  if (error) return <div className="text-red-600">Failed to load workflow.</div>;
  if (!wf) return <EmptyState title="Workflow not found" description="Please select another workflow." />;

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col gap-4">
        <div>
          <h2 className="text-xl font-semibold">{wf.name}</h2>
          {wf.description && (
            <p className="text-muted-foreground">{wf.description}</p>
          )}
        </div>
        <div ref={editorWrapperRef} className="min-h-0 flex-1">
          <WorkflowEditor
            key={wf.id}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeAdd={handleNodeAdd}
            onSave={handleSave}
            isSaving={isSaving}
            onPaneClick={onPaneClick}
            onNodeContextMenu={onNodeContextMenu}
          />
        </div>
        {menu && (
          <ContextMenu
            anchor={menu}
            onDelete={deleteNode}
            onClose={() => setMenu(null)}
            items={contextMenuItems}
          />
        )}
      </div>
    </ReactFlowProvider>
  );
}
