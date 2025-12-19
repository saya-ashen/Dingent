import type { AxiosInstance } from "axios";
import { PluginManifest } from "../types";

export class PluginsApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /** GET / */
  async list(): Promise<PluginManifest[]> {
    const { data } = await this.http.get<PluginManifest[]>(this.url("/"));
    return data || [];
  }

  /** DELETE /:id */
  async delete(pluginId: string): Promise<void> {
    await this.http.delete(this.url(`/${pluginId}`));
  }
}
