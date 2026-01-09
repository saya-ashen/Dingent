import {
  createHttpClient,
  UnauthorizeHandler,
  attachAuthInterceptor,
} from "./http";
import type { ApiClientConfig } from "./config";
import { AuthApi } from "./auth";
import {
  AssistantsApi,
  WorkflowsApi,
  SettingsApi,
  LogsApi,
  MarketApi,
  OverviewApi,
  PluginsApi,
  ModelsApi,
} from "./dashboard";
import { WorkspaceApi } from "./workspace";
import { ThreadsApi } from "./frontend";
import { AxiosInstance } from "axios";

export * from "./dashboard";
interface WorkspaceOptions {
  isGuest?: boolean;
  visitorId?: string;
}

export class ApiClient {
  public http: AxiosInstance;
  public auth: AuthApi;
  public workspaces: WorkspaceApi;

  private onUnauthorized?: UnauthorizeHandler;

  constructor(
    config: ApiClientConfig,
    token?: string | null,
    xVisitorId?: string | null,
    on401?: UnauthorizeHandler,
  ) {
    this.onUnauthorized = on401;
    this.http = createHttpClient(config, on401);
    this.auth = new AuthApi(this.http);
    this.workspaces = new WorkspaceApi(this.http, "/workspaces");
    if (token) {
      this.http.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }
    if (xVisitorId) {
      this.http.defaults.headers.common["X-Visitor-ID"] = xVisitorId;
    }
  }

  public forWorkspace(slug: string, options?: WorkspaceOptions) {
    const wsPath = `/${slug}`;
    const visitorId = options?.visitorId;
    const isGuest = options?.isGuest;

    let clientHttp = this.http;
    if (isGuest) {
      clientHttp = this.http.create();
      attachAuthInterceptor(clientHttp, this.onUnauthorized);

      clientHttp.interceptors.request.use((config: any) => {
        config.headers = config.headers || {};
        config.headers["X-Visitor-ID"] = visitorId;
        return config;
      });
    }

    return {
      threads: new ThreadsApi(clientHttp, `${wsPath}/chat/threads`),

      overview: new OverviewApi(this.http, `${wsPath}/overview`),
      assistants: new AssistantsApi(this.http, `${wsPath}/assistants`),
      workflows: new WorkflowsApi(this.http, `${wsPath}/workflows`),
      plugins: new PluginsApi(this.http, `${wsPath}/plugins`),
      logs: new LogsApi(this.http, `${wsPath}/logs`),
      settings: new SettingsApi(this.http, `${wsPath}/settings`),
      market: new MarketApi(this.http, `${wsPath}/market`),
      models: new ModelsApi(this.http, `${wsPath}/llms`),
    };
  }
}
