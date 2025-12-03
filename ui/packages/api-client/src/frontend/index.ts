import type { AxiosInstance } from "axios";
import { createArtifactsApi } from "./artifact";
const join = (a: string, b: string) =>
  a.replace(/\/+$/, "") + "/" + b.replace(/^\/+/, "");

export function createFrontendApi(http: AxiosInstance, dashboardBase: string) {
  const paths = {
    artifacts: join(dashboardBase, "/artifacts"),
  };
  return {
    artifacts: createArtifactsApi(http, paths.artifacts),
  };


}

export type FrontendApi = ReturnType<typeof createFrontendApi>;
