import type { AxiosInstance } from "axios";
import type { OverviewData, AnalyticsData } from "../types";

export function createOverviewApi(http: AxiosInstance, base: string) {
  const url = (p: string) => `${base}${p}`;

  return {
    async getOverview(): Promise<OverviewData> {
      const { data } = await http.get<OverviewData>(url("/"));
      return data;
    },

    async getBudget(): Promise<AnalyticsData> {
      const { data } = await http.get<AnalyticsData>(url("/budget"));
      return data;
    },
  };
}

