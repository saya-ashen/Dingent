import { AuthHooks } from "./http";

export type ApiClientConfig = {
  /** e.g. "/api/v1" or "https://api.example.com/api/v1" */
  baseURL: string;
  /** where we read/write the bearer token */
  tokenKey?: string;
  /** subpaths for feature groups */
  paths?: {
    dashboard?: string; // default: "/dashboard"
    market?: string;    // default: "/market"
    logs?: string;      // default: "/logs"
    workflows?: string; // default: "/workflows"
    plugins?: string;   // default: "/plugins"
    auth?: string;      // default: "/auth"
  };
  /** request timeout in ms */
  timeoutMs?: number;
};

