import {
  createHttpClient,
  AuthHooks,
  TokenProvider,
  UnauthorizeHandler,
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
} from "./dashboard";
import { WorkspaceApi } from "./workspace";
import { ThreadsApi } from "./frontend";
import { AxiosInstance } from "axios";

export * from "./dashboard";
interface WorkspaceOptions {
  visitorId?: string;
}

export class ApiClient {
  public http: AxiosInstance;
  public auth: AuthApi;
  public workspaces: WorkspaceApi;

  constructor(
    config: ApiClientConfig,
    getToken: TokenProvider,
    on401?: UnauthorizeHandler,
  ) {
    this.http = createHttpClient(config, getToken, on401);
    this.auth = new AuthApi(this.http);
    this.workspaces = new WorkspaceApi(this.http, "/workspaces");
  }

  public forWorkspace(slug: string, options?: WorkspaceOptions) {
    const wsPath = `/${slug}`;
    const visitorId = options?.visitorId;
    const isGuest = !!visitorId;

    // 1. 准备 HTTP 客户端
    // 如果是游客，我们需要确保请求头带上 X-Visitor-ID
    let clientHttp = this.http;
    if (isGuest) {
      // 继承原有的配置创建一个新实例，避免污染全局 http 对象
      // 注意：这假设 this.http 是一个 Axios 实例
      clientHttp = this.http.create();

      // 添加游客专属拦截器
      clientHttp.interceptors.request.use((config: any) => {
        config.headers = config.headers || {};
        config.headers["X-Visitor-ID"] = visitorId;
        return config;
      });
    }

    // 2. 动态计算路径策略
    // 游客走 /guest/threads，普通用户走 /threads
    // 注意：根据之前的 backend 代码，游客路由是 .../chat/guest/threads
    const threadsPath = isGuest
      ? `${wsPath}/chat/guest/threads`
      : `${wsPath}/chat/threads`;
    return {
      threads: new ThreadsApi(clientHttp, threadsPath),

      overview: new OverviewApi(this.http, `${wsPath}/overview`),
      assistants: new AssistantsApi(this.http, `${wsPath}/assistants`),
      workflows: new WorkflowsApi(this.http, `${wsPath}/workflows`),
      plugins: new PluginsApi(this.http, `${wsPath}/plugins`),
      logs: new LogsApi(this.http, `${wsPath}/logs`),
      settings: new SettingsApi(this.http, `${wsPath}/settings`),
      market: new MarketApi(this.http, `${wsPath}/market`),
    };
  }
}
