import type { AxiosInstance } from "axios";
import type { Workflow, WorkflowSummary } from "../types";

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
      const { data } = await http.get<Workflow>(url(`/${id}`));
      return data;
    },

    async save(wf: Workflow): Promise<WorkflowSummary> {
      try {
        const nodes = wf.nodes.map(n => ({ assistantId: n.data.assistantId, position: n.position, type: n.type, measured: n.measured, isStartNode: n.data.isStart }));
        const edges = wf.edges.map(e => ({ source: e.source, target: e.target, sourceHandle: e.sourceHandle, targetHandle: e.targetHandle }));
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

