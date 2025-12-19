import type { AxiosInstance } from "axios";
import type { OverviewData, AnalyticsData } from "../types";

export class OverviewApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /** GET / */
  async get(): Promise<OverviewData> {
    const { data } = await this.http.get<OverviewData>(this.url("/"));
    return data;
  }

  /** GET /budget */
  async getBudget(): Promise<AnalyticsData> {
    const { data } = await this.http.get<AnalyticsData>(this.url("/budget"));
    return data;
  }
}
