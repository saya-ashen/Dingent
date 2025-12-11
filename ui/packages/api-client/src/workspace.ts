import type { AxiosInstance } from "axios";
import type {
  Workspace,
  WorkspaceCreatePayload,
  WorkspaceInvitePayload,
  WorkspaceMember,
  WorkspaceUpdatePayload,
} from "./types";

export function createWorkspacesApi(http: AxiosInstance, workspacesBase: string) {
  const url = (p = "") => `${workspacesBase}${p}`;

  return {
    async updateWorkspace(
      id: string,
      payload: WorkspaceUpdatePayload
    ): Promise<Workspace> {
      const { data } = await http.patch<Workspace>(url(`/${id}`), payload);
      return data;
    },
    async listMembers(id: string): Promise<WorkspaceMember[]> {
      const { data } = await http.get<WorkspaceMember[]>(url(`/${id}/members`));
      return data;
    },
    async inviteMember(
      id: string,
      payload: WorkspaceInvitePayload
    ): Promise<WorkspaceMember> {
      const { data } = await http.post<WorkspaceMember>(
        url(`/${id}/members`),
        payload
      );
      return data;
    },
    async removeMember(id: string, userId: string): Promise<void> {
      await http.delete(url(`/${id}/members/${userId}`));
    },
  };
}

export class WorkspaceApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  async list(): Promise<Workspace[]> {
    const { data } = await this.http.get<Workspace[]>(this.url("/"));
    return data;
  }
  async getBySlug(slug: string): Promise<Workspace> {
    const { data } = await this.http.get<Workspace>(this.url(`/${slug}`));
    return data;
  }
  async create(payload: WorkspaceCreatePayload): Promise<Workspace> {
    const { data } = await this.http.post<Workspace>(this.url("/"), payload);
    return data;
  }
  async get(id: string): Promise<Workspace> {
    const { data } = await this.http.get<Workspace>(this.url(`/${id}`));
    return data;
  }

}

