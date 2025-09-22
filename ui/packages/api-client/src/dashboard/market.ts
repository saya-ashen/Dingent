import type { AxiosInstance } from "axios";
import type { MarketItem, MarketMetadata, MarketDownloadRequest, MarketDownloadResponse } from "../types";

export function createMarketApi(http: AxiosInstance, marketBase: string) {
  const url = (p = "") => `${marketBase}${p}`;

  return {
    async getMetadata(): Promise<MarketMetadata | null> {
      try {
        const { data } = await http.get<MarketMetadata>(url("/metadata"));
        return data;
      } catch (err) {
        console.warn("Backend not available, return mock metadata", err);
        return {
          version: "1.0.0",
          updated_at: new Date().toISOString(),
          categories: { plugins: 15, assistants: 8, workflows: 5 },
        };
      }
    },

    async list(category: "all" | "plugin" | "assistant" | "workflow"): Promise<MarketItem[]> {
      try {
        const path = category ? `/items?category=${category}` : "/items";
        const { data } = await http.get<MarketItem[]>(url(path));
        return data;
      } catch (err) {
        console.warn("Backend not available, return []", err);
        return [];
      }
    },

    async download(req: MarketDownloadRequest): Promise<MarketDownloadResponse> {
      const { data } = await http.post<MarketDownloadResponse>(url("/download"), req);
      return data;
    },

    async readme(itemId: string): Promise<string | null> {
      try {
        const { data } = await http.get<{ readme: string }>(url(`/items/${itemId}/readme`));
        return data.readme;
      } catch (err) {
        console.warn("Failed to fetch readme", itemId, err);
        return null;
      }
    },
  };
}



