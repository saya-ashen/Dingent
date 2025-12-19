import type { AxiosInstance } from "axios";
import type { LogItem, LogStats } from "../types";

export class LogsApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /** GET / */
  async list(params?: { level?: string; module?: string; limit?: number; search?: string }): Promise<LogItem[]> {
    const { data } = await this.http.get<LogItem[]>(this.url(""), { params });
    return data;
  }

  /** GET /stats */
  async stats(): Promise<LogStats> {
    const { data } = await this.http.get<LogStats>(this.url("/stats"));
    return data;
  }

  /** DELETE /clear */
  async clear(): Promise<true> {
    await this.http.delete(this.url("/clear"));
    return true;
  }
}
