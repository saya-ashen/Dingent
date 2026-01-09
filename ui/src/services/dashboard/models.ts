import {
  LLMModelConfig,
  LLMModelConfigCreate,
  LLMModelConfigUpdate,
  TestConnectionRequest,
  TestConnectionResponse,
} from "@/types/entity";
import type { AxiosInstance } from "axios";

export class ModelsApi {
  constructor(
    private http: AxiosInstance,
    private basePath: string = "",
  ) {}

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  async list(): Promise<LLMModelConfig[]> {
    const { data } = await this.http.get<LLMModelConfig[]>(this.url(""));
    return data;
  }

  async create(payload: LLMModelConfigCreate): Promise<LLMModelConfig> {
    const { data } = await this.http.post<LLMModelConfig>(
      this.url(""),
      payload,
    );
    return data;
  }

  async update(
    id: string,
    payload: LLMModelConfigUpdate,
  ): Promise<LLMModelConfig> {
    const { data } = await this.http.patch<LLMModelConfig>(
      this.url(`/${id}`),
      payload,
    );
    return data;
  }

  async delete(id: string): Promise<{ ok: boolean }> {
    const { data } = await this.http.delete<{ ok: boolean }>(this.url(`/${id}`));
    return data;
  }

  async testConnection(
    payload: TestConnectionRequest,
  ): Promise<TestConnectionResponse> {
    const { data } = await this.http.post<TestConnectionResponse>(
      this.url("/test"),
      payload,
    );
    return data;
  }
}
