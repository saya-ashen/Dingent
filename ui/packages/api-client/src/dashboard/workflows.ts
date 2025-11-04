import type { AxiosInstance } from "axios";
import type { Workflow, WorkflowEdge, WorkflowNode, WorkflowSummary } from "../types";

type WorkflowNodeDTO = {
  id: string;               // 节点ID（不是 assistantId）
  assistantId: string;
  name: string;
  type: "assistant";
  isStartNode?: boolean;    // 后端字段：isStartNode
  position: { x: number; y: number };
  workflowId: string;
  description?: string;
};
type WorkflowEdgeDTO = {
  id: string;
  workflowId: string;
  targetNodeId: string;
  targetHandle: string | null;
  sourceNodeId: string;
  sourceHandle: string | null;
  type: string;
};
type WorkflowDTO = {
  id: string;
  name: string;
  description: string | null;
  created_at?: string;
  updated_at?: string;
  nodes: WorkflowNodeDTO[];
  edges: any[]; // 按需细化
};
function toWorkflowNode(n: WorkflowNodeDTO): WorkflowNode {
  return {
    id: n.id,
    type: "assistant",
    position: n.position,
    data: {
      id: n.id,
      assistantId: n.assistantId,
      name: n.name,
      isStart: n.isStartNode ?? false,
      description: n.description || "",
    },
  };
}
function toWorkflowEdge(e: WorkflowEdgeDTO): WorkflowEdge {
  return {
    id: e.id,
    source: e.sourceNodeId,
    target: e.targetNodeId,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
    type: e.type,
    data: { mode: "single" },
  }
}
function toWorkflow(dto: WorkflowDTO): Workflow {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description ?? undefined,
    created_at: dto.created_at,
    updated_at: dto.updated_at,
    nodes: dto.nodes.map(toWorkflowNode),
    edges: dto.edges.map(toWorkflowEdge),
  };
}
export function createWorkflowsApi(http: AxiosInstance, base: string) {
  const url = (p: string) => `${base}${p}`;

  return {
    async list(): Promise<Workflow[]> {
      try {
        const { data } = await http.get<Workflow[]>(url(""));
        return data;
      } catch (err) {
        console.warn("Backend not available, returning []", err);
        return [];
      }
    },

    async get(id: string): Promise<Workflow | null> {
      const { data } = await http.get<WorkflowDTO>(url(`/${id}`));
      return data ? toWorkflow(data) : null;
    },

    async save(wf: Workflow): Promise<WorkflowSummary> {
      try {
        const nodes = wf.nodes.map(n => ({ id: n.id, assistantId: n.data.assistantId, position: n.position, type: n.type, measured: n.measured, isStartNode: n.data.isStart }));
        const edges = wf.edges.map(e => ({ sourceNodeId: e.source, targetNodeId: e.target, sourceHandle: e.sourceHandle, targetHandle: e.targetHandle }));
        const { data } = await http.put<WorkflowSummary>(url(`/${wf.id}`), { name: wf.name, description: wf.description, nodes: nodes, edges: edges, });
        return data;
      } catch {
        console.warn("Backend not available, mocking save");
        return { ...wf, };
      }
    },

    async create(name: string, description?: string): Promise<Workflow> {
      try {
        const { data } = await http.post<Workflow>(url(""), { name, description });
        return data;
      } catch {
        console.warn("Backend not available, mocking create");
        const now = new Date().toISOString();
        return { id: `mock-${Date.now()}`, name, description, nodes: [], edges: [], created_at: now, updated_at: now };
      }
    },

    async remove(id: string): Promise<void> {
      try {
        await http.delete(url(`/${id}`));
      } catch {
        console.warn("Backend not available, mocking delete");
      }
    },
  };
}

