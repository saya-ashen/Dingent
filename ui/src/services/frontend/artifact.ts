import type { AxiosInstance, AxiosRequestConfig } from "axios";
import { Artifact } from "../types";

export class ArtifactApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  async get(id: string, config?: AxiosRequestConfig): Promise<Artifact> {
    const { data } = await this.http.get<Artifact>(this.url(`/${id}`), config);
    return data;
  }
}
