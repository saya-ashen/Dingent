import { ChatThread } from "@/types/entity";
import type { AxiosInstance } from "axios";

type UpdateThreadDto = {
  title: string;
};

export class ThreadsApi {
  constructor(
    private http: AxiosInstance,
    private basePath: string = "/threads"
  ) { }

  /**
   * 辅助方法：拼接 URL
   */
  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /**
   * GET /threads
   * 获取当前用户的对话历史列表
   */
  async list(): Promise<ChatThread[]> {
    const { data } = await this.http.get<ChatThread[]>(this.url());
    return data;
  }

  /**
   * DELETE /threads/:id
   * 删除指定对话
   */
  async delete(id: string): Promise<void> {
    await this.http.delete(this.url(`/${id}`));
  }
  async deleteAll(): Promise<void> {
    await this.http.delete(this.url(`/`));
  }

  async update(id: string, dto: UpdateThreadDto): Promise<ChatThread> {
    const { data } = await this.http.patch<ChatThread>(this.url(`/${id}`), dto);
    return data;
  }

  async get(id: string): Promise<ChatThread> {
    const { data } = await this.http.get<ChatThread>(this.url(`/${id}`));
    return data;
  }
}
