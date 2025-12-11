import type { AxiosInstance } from "axios";
import type { LoginRequest, LoginResponse, SignupRequest } from "./types";

export class AuthApi {
  constructor(private http: AxiosInstance) { }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const params = new URLSearchParams();
    params.append("username", credentials.email);
    params.append("password", credentials.password);

    const { data } = await this.http.post<LoginResponse>("/auth/token", params);
    return data; // 只返回数据，不操作 Store
  }

  async signup(payload: SignupRequest) {
    const { data } = await this.http.post("/auth/register", payload);
    return data;
  }

  async getMe() {
    const { data } = await this.http.get("/users/me");
    return data;
  }
}

