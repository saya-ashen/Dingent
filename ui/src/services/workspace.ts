import {
  Workspace,
  WorkspaceCreatePayload,
  WorkspaceInvitePayload,
  WorkspaceMember,
  WorkspaceUpdatePayload,
} from "@/types/entity";
import type { AxiosInstance } from "axios";

export class WorkspaceApi {
  constructor(
    private http: AxiosInstance,
    private basePath: string = "",
  ) {}

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  async list(): Promise<Workspace[]> {
    const { data } = await this.http.get<Workspace[]>(this.url(""));
    return data;
  }
  async update(
    slug: string,
    payload: WorkspaceUpdatePayload,
  ): Promise<Workspace> {
    const { data } = await this.http.patch<Workspace>(
      this.url(`/${slug}`),
      payload,
    );
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
