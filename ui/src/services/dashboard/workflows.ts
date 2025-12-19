import type { AxiosInstance } from "axios";
import type { Workflow, WorkflowEdge, WorkflowNode, WorkflowSummary } from "../types";

// --- DTO Types (Internal) ---
interface WorkflowNodeDTO {
  id: string;
  assistantId: string;
  name: string;
  type: "assistant";
  isStartNode?: boolean;
  position: { x: number; y: number };
  workflowId: string;
  description?: string;
}

interface WorkflowEdgeDTO {
  id: string;
  workflowId: string;
  targetNodeId: string;
  targetHandle: string | null;
  sourceNodeId: string;
  sourceHandle: string | null;
  type: string;
  mode: "single" | "bidirectional";
}

interface WorkflowDTO {
  id: string;
  name: string;
  description: string | null;
  created_at?: string;
  updated_at?: string;
  nodes: WorkflowNodeDTO[];
  edges: any[];
}

export class WorkflowsApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /** GET / */
  async list(): Promise<Workflow[]> {
    // 假设列表接口返回的是简化版或完整版，这里假设是完整版并包含 DTO 转换
    // 如果列表返回结构不同，需调整
    const { data } = await this.http.get<Workflow[]>(this.url(""));
    return data;
  }

  /** GET /:id */
  async get(id: string): Promise<Workflow> {
    const { data } = await this.http.get<WorkflowDTO>(this.url(`/${id}`));
    return this.transformToDomain(data);
  }

  /** POST / */
  async create(payload: { name: string; description?: string }): Promise<Workflow> {
    const { data } = await this.http.post<Workflow>(this.url(""), payload);
    return data;
  }

  /** PUT /:id */
  async update(wf: Workflow): Promise<WorkflowSummary> {
    // Transform Domain -> DTO
    const payload = {
      name: wf.name,
      description: wf.description,
      nodes: wf.nodes.map((n) => ({
        id: n.id,
        assistantId: n.data.assistantId,
        position: n.position,
        type: n.type,
        measured: n.measured,
        isStartNode: n.data.isStart,
      })),
      edges: wf.edges.map((e) => ({
        sourceNodeId: e.source,
        targetNodeId: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
        mode: e.data?.mode,
      })),
    };

    const { data } = await this.http.put<WorkflowSummary>(this.url(`/${wf.id}`), payload);
    return data;
  }

  /** DELETE /:id */
  async delete(id: string): Promise<void> {
    await this.http.delete(this.url(`/${id}`));
  }

  // --- Private Transformers ---

  private transformToDomain(dto: WorkflowDTO): Workflow {
    return {
      id: dto.id,
      name: dto.name,
      description: dto.description ?? undefined,
      created_at: dto.created_at,
      updated_at: dto.updated_at,
      nodes: dto.nodes.map(this.transformNode),
      edges: dto.edges.map(this.transformEdge),
    };
  }

  private transformNode(n: WorkflowNodeDTO): WorkflowNode {
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

  private transformEdge(e: WorkflowEdgeDTO): WorkflowEdge {
    return {
      id: e.id,
      source: e.sourceNodeId,
      target: e.targetNodeId,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
      type: e.type,
      data: { mode: e.mode },
    };
  }
}
