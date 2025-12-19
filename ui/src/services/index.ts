import { createHttpClient, AuthHooks, TokenProvider, UnauthorizeHandler } from "./http";
import type { ApiClientConfig } from "./config";
import { AuthApi } from "./auth";
import { AssistantsApi, WorkflowsApi, SettingsApi, LogsApi, MarketApi, OverviewApi, PluginsApi } from "./dashboard";
import { WorkspaceApi } from "./workspace";
import { ThreadsApi } from "./frontend";


export * from "./dashboard";

export class ApiClient {
  public http: any;
  public auth: AuthApi;
  public workspaces: WorkspaceApi;

  constructor(config: ApiClientConfig, getToken: TokenProvider, on401?: UnauthorizeHandler) {
    this.http = createHttpClient(config, getToken, on401);
    this.auth = new AuthApi(this.http);
    this.workspaces = new WorkspaceApi(this.http, "/workspaces");
  }

  public forWorkspace(slug: string) {
    const wsPath = `/${slug}`;
    return {
      overview: new OverviewApi(this.http, `${wsPath}/overview`),
      assistants: new AssistantsApi(this.http, `${wsPath}/assistants`),
      workflows: new WorkflowsApi(this.http, `${wsPath}/workflows`),
      plugins: new PluginsApi(this.http, `${wsPath}/plugins`),
      logs: new LogsApi(this.http, `${wsPath}/logs`),
      settings: new SettingsApi(this.http, `${wsPath}/settings`),
      market: new MarketApi(this.http, `${wsPath}/market`),
      threads: new ThreadsApi(this.http, `${wsPath}/chat/threads`),
    };
  }
}
