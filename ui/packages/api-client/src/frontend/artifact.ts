import type { AxiosInstance, AxiosRequestConfig } from "axios";
import { Artifact } from "../types";

export function createArtifactsApi(http: AxiosInstance, artifactsBase: string) {
  const url = (p = "") => `${artifactsBase}${p}`;

  return {
    /**
     * Fetches a single artifact by its ID.
     * @param id - The ID of the artifact to fetch.
     * @param config - Optional Axios request config, e.g., for cancellation.
     */
    async get(id: string, config?: AxiosRequestConfig): Promise<Artifact> {
      // 1. Changed the return type from Artifact[] to Artifact.
      // 2. The endpoint seems to be /api/resource/{id}, so your http instance
      //    should be configured with the base URL /api.
      //    And artifactsBase should probably be "/resource"
      const { data } = await http.get<Artifact>(url(`/${id}`), config);
      return data;
    },
  };
}
