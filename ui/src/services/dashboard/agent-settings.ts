import { AppSettings } from "@/types/entity";
import type { AxiosInstance } from "axios";

export class SettingsApi {
  constructor(private http: AxiosInstance, private basePath: string = "") { }

  private url(path: string = ""): string {
    return `${this.basePath}${path}`;
  }

  /** GET / */
  async get(): Promise<AppSettings | null> {
    const { data } = await this.http.get<AppSettings>(this.url("/"));
    return data;
  }

  /** PATCH / */
  async update(payload: AppSettings): Promise<void> {
    await this.http.patch(this.url("/"), payload);
  }
}
