import type { AxiosInstance } from "axios";
import type {
  Workspace,
  WorkspaceCreatePayload,
  WorkspaceInvitePayload,
  WorkspaceMember,
  WorkspaceUpdatePayload,
} from "../types";

export function createWorkspacesApi(http: AxiosInstance, workspacesBase: string) {
  const url = (p = "") => `${workspacesBase}${p}`;

  return {
    /**
     * 获取当前用户的所有工作空间列表
     */
    async listWorkspaces(): Promise<Workspace[]> {
      const { data } = await http.get<Workspace[]>(url("/"));
      return data;
    },

    /**
     * 创建一个新的工作空间
     */
    async createWorkspace(payload: WorkspaceCreatePayload): Promise<Workspace> {
      const { data } = await http.post<Workspace>(url("/"), payload);
      return data;
    },

    /**
     * 获取指定工作空间的详情
     */
    async getWorkspace(id: string): Promise<Workspace> {
      const { data } = await http.get<Workspace>(url(`/${id}`));
      return data;
    },

    /**
     * 更新工作空间信息 (Admin/Owner only)
     */
    async updateWorkspace(
      id: string,
      payload: WorkspaceUpdatePayload
    ): Promise<Workspace> {
      const { data } = await http.patch<Workspace>(url(`/${id}`), payload);
      return data;
    },

    /**
     * 获取成员列表
     */
    async listMembers(id: string): Promise<WorkspaceMember[]> {
      const { data } = await http.get<WorkspaceMember[]>(url(`/${id}/members`));
      return data;
    },

    /**
     * 邀请成员 (Admin/Owner only)
     */
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
    async getBySlug(slug: string): Promise<Workspace> {
      const { data } = await http.get<Workspace>(url(`/${slug}`));
      return data;
    },

    /**
     * 移除成员 或 自己离开 (Admin/Owner only, or self)
     */
    async removeMember(id: string, userId: string): Promise<void> {
      await http.delete(url(`/${id}/members/${userId}`));
    },
  };
}
