import type { AxiosInstance } from "axios";
import type { LoginRequest, LoginResponse } from "./types";
import type { TokenStorage } from "./storage";

export function createAuthApi(http: AxiosInstance, opts: {
  authPath: string; // e.g. "/auth"
  tokenStore: TokenStorage;
  tokenKey?: string; // informational
}) {
  return {
    /** POST /auth/token (x-www-form-urlencoded) */
    async login(credentials: LoginRequest): Promise<LoginResponse> {
      const params = new URLSearchParams();
      params.append("username", credentials.email);
      params.append("password", credentials.password);

      const { data } = await http.post<LoginResponse>(
        `${opts.authPath}/token`,
        params,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );

      // persist token if present
      if (data && (data as any).access_token) {
        opts.tokenStore.set((data as any).access_token);
      }
      return data;
    },

    /** optional helper */
    logout() {
      opts.tokenStore.set(null);
    },
  };
}
