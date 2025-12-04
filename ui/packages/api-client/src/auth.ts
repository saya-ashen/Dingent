import type { AxiosInstance } from "axios";
import type { LoginRequest, LoginResponse, AuthUser, SignupRequest, SignupResponse } from "./types";
import { setAccessToken, setUser, resetAuth } from "@repo/store";


export function createAuthApi(http: AxiosInstance, opts: { authPath: string; }) {
  return {
    /** POST /auth/token */
    async login(credentials: LoginRequest): Promise<LoginResponse> {
      const params = new URLSearchParams();
      params.append("username", credentials.email);
      params.append("password", credentials.password);

      const { data } = await http.post<LoginResponse>(
        `${opts.authPath}/token`,
        params,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );

      if (data?.access_token) {
        setAccessToken(data.access_token);
        // const userProfile = await this.getMe();
        // setUser(userProfile);
      }
      return data;
    },
    /** * POST /auth/register 
     */
    async signup(payload: SignupRequest): Promise<SignupResponse> {
      const { data } = await http.post<SignupResponse>(
        `${opts.authPath}/register`,
        payload
      );

      return data;
    },

    /** Call the store's reset action */
    logout() {
      resetAuth();
    },

    /** Example function to get the current user */
    async getMe(): Promise<AuthUser> {
      const { data } = await http.get<AuthUser>('/users/me');
      // Update the user in the store
      setUser(data);
      return data;
    }
  };
}
