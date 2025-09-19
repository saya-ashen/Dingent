import type { AxiosInstance } from "axios";
import type { LoginRequest, LoginResponse } from "./types/index.ts";
import { extractErrorMessage } from "./http";

/**
 * Creates an authentication API client.
 * @param http The Axios instance to use for requests.
 * @returns An object with authentication methods.
 */
export function createAuthApi(http: AxiosInstance) {
  return {
    /**
     * Logs in a user and returns the user data and token.
     */
    login: async (credentials: LoginRequest): Promise<LoginResponse> => {
      try {
        const params = new URLSearchParams();
        params.append("username", credentials.email);
        params.append("password", credentials.password);

        // The path is relative to the baseURL of the passed http instance
        const { data } = await http.post<LoginResponse>("/auth/token", params, {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        });
        return data;
      } catch (err) {
        throw new Error(`Login failed: ${extractErrorMessage(err)}`);
      }
    },

    // You can add other auth-related functions here, e.g., logout(), register()
  };
}
