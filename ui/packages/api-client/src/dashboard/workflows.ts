import type { AxiosInstance } from "axios";
import type { Workflow } from "../types";

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

    async save(wf: Workflow): Promise<Workflow> {
      try {
        const { data } = await http.put<Workflow>(url(`/${wf.id}`), wf);
        return data;
      } catch {
        console.warn("Backend not available, mocking save");
        return { ...wf, updated_at: new Date().toISOString() };
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

