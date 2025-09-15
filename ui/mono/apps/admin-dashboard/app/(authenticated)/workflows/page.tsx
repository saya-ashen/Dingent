"use client";
import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import {
  getWorkflows,
  getAssistantsConfig,
  createWorkflow,
  saveWorkflow,
  deleteWorkflow,
  Workflow,
  WorkflowNode,
  WorkflowEdge,
} from "@repo/api-client";
import {
  ConfigDrawer,
  EmptyState,
  Header,
  Main,
  LoadingSkeleton,
  ProfileDropdown,
  Search,
  ThemeSwitch,
} from "@repo/ui/components";
import {
  AssistantsPalette,
  ContextMenu,
  NewWorkflowDialog,
  WorkflowEditor,
  WorkflowList,
} from "@repo/ui/dashboard";
export default function WorkflowsPages() {
  const qc = useQueryClient();

  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(
    null,
  );
  const editorWrapperRef = useRef<HTMLDivElement | null>(null);
  const [menu, setMenu] = useState<null | { id: string; x: number; y: number }>(
    null,
  );

  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);

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

  useEffect(() => {
    if (selectedWorkflow) {
      const rawNodes = structuredClone(selectedWorkflow.nodes ?? []);
      let hasStart = false;
      const normalized = rawNodes.map((n: any) => {
        if (n.type === "start" || n.data?.isStart) {
          hasStart = true;
          return {
            ...n,
            type: "assistant",
            data: {
              ...(n.data || {}),
              isStart: true,
            },
          };
        }
        return {
          ...n,
          type: "assistant",
          data: {
            ...(n.data || {}),
            isStart: n.data?.isStart === true,
          },
        };
      });
      if (!hasStart && normalized.length > 0) {
        normalized[0].data.isStart = true;
      }
      setNodes(normalized);
      setEdges(structuredClone(selectedWorkflow.edges ?? []));
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [selectedWorkflow]);

  const createWorkflowMutation = useMutation({
    mutationFn: ({
      name,
      description,
    }: {
      name: string;
      description?: string;
    }) => createWorkflow(name, description),
    onSuccess: (newWorkflow) => {
      toast.success("Workflow created");
      qc.invalidateQueries({ queryKey: ["workflows"] });
      setSelectedWorkflow(newWorkflow);
    },
    onError: (error: Error) =>
      toast.error(`Failed to create workflow: ${error.message}`),
  });

  const saveWorkflowMutation = useMutation({
    mutationFn: saveWorkflow,
    onSuccess: () => {
      toast.success("Workflow saved");
      qc.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (error: Error) =>
      toast.error(`Failed to save workflow: ${error.message}`),
  });

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
          isStart: isFirst, // 第一个节点自动成为 start
        },
      };
      return [...prev, node];
    });
  }, []);

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
  }, []);

  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: any) => {
      event.preventDefault();
      setMenu({
        id: node.id,
        x: event.clientX,
        y: event.clientY,
      });
    },
    [],
  );

  const deleteNode = (id: string) => {
    const target = nodes.find((n) => n.id === id);
    if (target?.data?.isStart) {
      toast.warning("The Start node cannot be deleted.");
      setMenu(null);
      return;
    }
    setNodes((nodes) => nodes.filter((node) => node.id !== id));
    setEdges((edges) =>
      edges.filter((edge) => edge.source !== id && edge.target !== id),
    );
    setMenu(null);
  };

  const onPaneClick = useCallback(() => setMenu(null), []);

  const deleteWorkflowMutation = useMutation({
    mutationFn: deleteWorkflow,
    onSuccess: () => {
      toast.success("Workflow deleted");
      qc.invalidateQueries({ queryKey: ["workflows"] });
      setSelectedWorkflow(null);
    },
    onError: (error: Error) =>
      toast.error(`Failed to delete workflow: ${error.message}`),
  });

  const onNodesChange = useCallback(
    (changes: NodeChange<WorkflowNode>[]) => {
      const removeChanges = changes.filter(
        (change) =>
          change.type === "remove" &&
          nodes.find((n) => n.id === change.id)?.data?.isStart,
      );
      if (removeChanges.length > 0) {
        toast.warning("The Start node cannot be deleted.");
        return;
      }
      setNodes((nds) => applyNodeChanges<WorkflowNode>(changes, nds));
    },
    [nodes],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      // --- Start of Debugging Output ---

      // Log the array of changes received from React Flow
      console.log("onEdgesChange triggered. Changes:", changes);

      // You can also inspect the state *before* the changes are applied
      setEdges((currentEdges) => {
        console.log("Edges before applying changes:", currentEdges);
        const nextEdges = applyEdgeChanges(changes, currentEdges);
        console.log("Edges after applying changes:", nextEdges);
        return nextEdges;
      });
    },
    [setEdges], // It's good practice to include the setter in the dependency array
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
            id: `e-${source}->${target}`,
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
          if (existing.data?.mode === "bidirectional") {
            toast.warning("This pair is already bidirectional.");
            return prev;
          }
          toast.warning("A connection in this direction already exists.");
          return prev;
        }
        if (existing.data?.mode !== "bidirectional") {
          return prev.map((e) =>
            e.id === existing.id
              ? { ...e, data: { ...(e.data || {}), mode: "bidirectional" } }
              : e,
          );
        }
        return prev;
      });
    },
    [nodes, edges],
  );

  const handleSaveWorkflow = () => {
    if (!selectedWorkflow) return;
    saveWorkflowMutation.mutate({
      ...selectedWorkflow,
      nodes,
      edges,
    });
  };

  const paletteAssistants = useMemo(() => {
    const nodeAssistantIds = new Set(
      nodes.map((n) => n.data?.assistantId).filter(Boolean),
    );
    return allAssistants.filter((a) => !nodeAssistantIds.has(a.id));
  }, [allAssistants, nodes]);

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
        disabled: isStart, // 再次保护
        onClick: deleteNode,
      },
    ];
  }, [menu, nodes, setStartNode]);

  if (workflowsQ.isLoading || assistantsQ.isLoading)
    return <LoadingSkeleton lines={5} />;
  if (workflowsQ.error || assistantsQ.error)
    return <div className="text-red-600">Failed to load data.</div>;

  return (
    <>
      <Header>
        <Search />
        <div className="ms-auto flex items-center gap-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>
      <Main>
        <ReactFlowProvider>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Workflows</h1>
            <p className="text-muted-foreground">
              Design and manage task handoff workflows between assistants
            </p>
          </div>
          <div className="mt-4 flex min-h-0 w-full flex-1 gap-8 px-4 md:px-8">
            <aside className="flex w-full max-w-3xs flex-shrink-0 flex-col gap-6">
              <NewWorkflowDialog
                onCreateWorkflow={createWorkflowMutation.mutate}
              />
              <WorkflowList
                workflows={workflows}
                selectedWorkflow={selectedWorkflow}
                onSelect={setSelectedWorkflow}
                onDelete={deleteWorkflowMutation.mutate}
              />
              <AssistantsPalette assistants={paletteAssistants} />
            </aside>

            <main className="min-h-0 flex-1">
              {selectedWorkflow ? (
                <div className="flex h-full flex-col gap-4">
                  <div>
                    <h2 className="text-xl font-semibold">
                      {selectedWorkflow.name}
                    </h2>
                    {selectedWorkflow.description && (
                      <p className="text-muted-foreground">
                        {selectedWorkflow.description}
                      </p>
                    )}
                  </div>
                  <div ref={editorWrapperRef} className="min-h-0 flex-1">
                    <WorkflowEditor
                      key={selectedWorkflow.id}
                      nodes={nodes}
                      edges={edges}
                      onNodesChange={onNodesChange}
                      onEdgesChange={onEdgesChange}
                      onConnect={onConnect}
                      onNodeAdd={handleNodeAdd}
                      onSave={handleSaveWorkflow}
                      isSaving={saveWorkflowMutation.isPending}
                      onPaneClick={onPaneClick}
                      onNodeContextMenu={onNodeContextMenu}
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
          {menu && (
            <ContextMenu
              anchor={menu}
              onDelete={deleteNode}
              onClose={() => setMenu(null)}
              items={contextMenuItems}
            />
          )}
        </ReactFlowProvider>
      </Main>
    </>
  );
}
