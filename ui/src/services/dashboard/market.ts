import {
  MarketDownloadRequest,
  MarketDownloadResponse,
  MarketItem,
  MarketMetadata,
} from "@/types/entity";
import type { AxiosInstance } from "axios";

export class MarketApi {
  constructor(
    private http: AxiosInstance,
    private basePath: string = "",
  ) {}

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /** GET /metadata */
  async getMetadata(): Promise<MarketMetadata> {
    const { data } = await this.http.get<MarketMetadata>(this.url("/metadata"));
    return data;
  }

  /** GET /items */
  async list(
    category: "all" | "plugin" | "assistant" | "workflow",
  ): Promise<MarketItem[]> {
    const path = `/items?category=${category}`;
    const { data } = await this.http.get<MarketItem[]>(this.url(path));
    return data;
  }

  /** POST /download */
  async download(req: MarketDownloadRequest): Promise<MarketDownloadResponse> {
    const { data } = await this.http.post<MarketDownloadResponse>(
      this.url("/download"),
      req,
    );
    return data;
  }

  /** GET /items/:id/readme */
  async getReadme(
    itemId: string,
    category: "plugin" | "assistant" | "workflow",
  ): Promise<string> {
    const { data } = await this.http.get<{ readme: string }>(
      this.url(`/items/${itemId}/readme`),
    );
    return data.readme;
  }
}
